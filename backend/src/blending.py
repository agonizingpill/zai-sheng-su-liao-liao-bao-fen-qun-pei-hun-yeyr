from decimal import Decimal
from datetime import datetime,timezone
from fastapi import HTTPException
from sqlalchemy import select,delete
from .models import Bale,Blend,BlendPortion,Audit
from .quality_models import SupplierLot,LotBale

def obj(x):return {c.name:float(getattr(x,c.name)) if isinstance(getattr(x,c.name),Decimal) else getattr(x,c.name) for c in x.__table__.columns}
def get(s,model,id,lock=False):
    q=select(model).where(model.id==id)
    if lock:q=q.with_for_update().execution_options(populate_existing=True)
    x=s.scalar(q)
    if not x:raise HTTPException(404,'记录不存在')
    return x
def audit(s,u,action,detail):s.add(Audit(actor=u['email'],action=action,detail=str(detail),at=datetime.now(timezone.utc).isoformat()))
def portions(s,b):return s.scalars(select(BlendPortion).where(BlendPortion.blend_id==b.id).order_by(BlendPortion.bale_id)).all()
def view(s,b):
    d=obj(b);ps=portions(s,b);d['portions']=[{**obj(p),'bale_code':s.get(Bale,p.bale_id).code} for p in ps];d['total_kg']=float(sum((p.kg for p in ps),Decimal(0)));return d
def set_portions(s,b,data,u):
    if b.status!='draft':raise HTTPException(409,'配方已审秤或已放行；先退回草稿才能调整')
    ids=[x.bale_id for x in data.portions]
    if len(set(ids))!=len(ids):raise HTTPException(409,'同一料包只能称入一次')
    bales={x.id:x for x in s.scalars(select(Bale).where(Bale.id.in_(ids)).order_by(Bale.id).with_for_update())}
    for p in data.portions:
        x=bales.get(p.bale_id)
        if not x:raise HTTPException(404,'所选料包不存在')
        if x.cluster_id is None:raise HTTPException(409,'料包尚未完成分群检验')
        if p.kg>x.available_kg:raise HTTPException(409,f'{x.code}可用重量不足，未保存配方')
    s.execute(delete(BlendPortion).where(BlendPortion.blend_id==b.id))
    for p in data.portions:
        x=bales[p.bale_id];s.add(BlendPortion(blend_id=b.id,bale_id=x.id,kg=p.kg,cluster_snapshot=x.cluster_id,version_snapshot=x.cluster_version,pvc_snapshot=x.pvc_ppm,melt_snapshot=x.melt_index,moisture_snapshot=x.moisture))
    b.weighted_pvc=None;s.flush();audit(s,u,'weighed',b.code);return view(s,b)
def validate(s,b,locked_bales=None):
    ps=portions(s,b)
    if not ps:raise HTTPException(409,'尚未选择料包，不能审秤')
    if len({(p.version_snapshot,p.cluster_snapshot) for p in ps})!=1:raise HTTPException(409,'跨群或跨分群版本选料，不能配混')
    total=sum((p.kg for p in ps),Decimal(0))
    if total!=b.target_kg:raise HTTPException(409,f'称入{total}kg与目标{b.target_kg}kg不一致')
    weighted=sum((p.kg*p.pvc_snapshot for p in ps),Decimal(0))/total
    if weighted>b.max_pvc:raise HTTPException(409,f'加权PVC {weighted:.3f}ppm超过配方上限{b.max_pvc}ppm')
    ids=sorted(p.bale_id for p in ps)
    if locked_bales is None:
        locked_bales={x.id:x for x in s.scalars(select(Bale).where(Bale.id.in_(ids)).order_by(Bale.id).with_for_update())}
    lot_ids=list(s.scalars(select(LotBale.lot_id).where(LotBale.bale_id.in_(ids)).distinct().order_by(LotBale.lot_id)))
    lots=list(s.scalars(select(SupplierLot).where(SupplierLot.id.in_(lot_ids)).order_by(SupplierLot.id).with_for_update().execution_options(populate_existing=True)))
    if any(x.state=='quarantine' for x in lots):raise HTTPException(409,'供应批次已隔离，不能审秤或最终投料放行')
    for p in ps:
        bale=locked_bales[p.bale_id] if locked_bales is not None else get(s,Bale,p.bale_id)
        if p.kg>bale.available_kg:raise HTTPException(409,f'{bale.code}可用重量不足，投料未扣减')
    return ps,weighted

def evaluate(s,b,u):
    if b.status!='draft':raise HTTPException(409,'只有草稿可审秤')
    _,weighted=validate(s,b);b.weighted_pvc=weighted;b.status='ready';audit(s,u,'checked',b.code);return view(s,b)
def release(s,b,u):
    if b.status!='ready':raise HTTPException(409,'配方须审秤通过且不可重复放行')
    ps=portions(s,b);ids=sorted(p.bale_id for p in ps)
    locked={x.id:x for x in s.scalars(select(Bale).where(Bale.id.in_(ids)).order_by(Bale.id).with_for_update().execution_options(populate_existing=True))}
    ps,weighted=validate(s,b,locked)
    for p in ps:locked[p.bale_id].available_kg-=p.kg
    b.status='released';b.weighted_pvc=weighted;b.released_by=u['email'];audit(s,u,'released',b.code);s.flush();return view(s,b)
