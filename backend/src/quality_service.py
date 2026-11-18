from decimal import Decimal
from datetime import datetime,timezone
from fastapi import HTTPException
from sqlalchemy import select
from .models import Bale,Blend,BlendPortion
from .quality_models import SupplierLot,LotBale,PelletCheck
from .blending import obj,get,audit,view

def lot_view(s,lot):
    return {**obj(lot),'bales':[{**obj(x),'bale_code':s.get(Bale,x.bale_id).code} for x in s.scalars(select(LotBale).where(LotBale.lot_id==lot.id).order_by(LotBale.bale_id))]}
def assign(s,lid,data,u):
    b=get(s,Bale,data.bale_id,True);lot=get(s,SupplierLot,lid,True)
    if lot.state!='active':raise HTTPException(409,'隔离批次不能接收新料包，先完成复核解除')
    if s.scalar(select(LotBale.id).where(LotBale.bale_id==b.id)):raise HTTPException(409,'料包已挂供应批次，追溯归属不可重挂')
    if s.scalar(select(BlendPortion.id).join(Blend,Blend.id==BlendPortion.blend_id).where(BlendPortion.bale_id==b.id,Blend.status=='released').limit(1)):raise HTTPException(409,'料包已经投料，禁止事后补挂或变更供应追溯')
    s.add(LotBale(lot_id=lot.id,bale_id=b.id,received_snapshot=obj(b)));s.flush();audit(s,u,'lot_assigned',lot.code+' / '+b.code);return lot_view(s,lot)
def decide_lot(s,lid,data,u,target):
    # Release and isolation serialize through bale locks followed by lot locks.
    ids=list(s.scalars(select(LotBale.bale_id).where(LotBale.lot_id==lid).order_by(LotBale.bale_id)))
    list(s.scalars(select(Bale).where(Bale.id.in_(ids)).order_by(Bale.id).with_for_update()))
    lot=get(s,SupplierLot,lid,True)
    if lot.state==target:raise HTTPException(409,'该批次已处于目标状态，不可重复确认')
    reason=data.reason.strip()
    if len(reason)<8:raise HTTPException(409,'请填写至少8字的隔离或解除依据')
    lot.state=target;lot.inspection_note=reason;audit(s,u,'lot_'+target,lot.code+' / '+reason);return lot_view(s,lot)
def pellet_view(s,x):return {**obj(x),'blend_code':s.get(Blend,x.blend_id).code}
def measure(s,x,data,u,reason):
    if data.actual_kg>Decimal(str(x.input_snapshot['total_kg'])):raise HTTPException(409,'粒料产出不能超过已放行实际投料总重')
    x.actual_kg=data.actual_kg;x.melt_index=data.melt_index;x.pvc_ppm=data.pvc_ppm
    x.state='quarantine' if data.pvc_ppm>x.input_snapshot['max_pvc'] else 'passed'
    record={'actual_kg':float(data.actual_kg),'melt_index':float(data.melt_index),'pvc_ppm':float(data.pvc_ppm),'result':x.state,'reason':reason,'actor':u['email'],'at':datetime.now(timezone.utc).isoformat()}
    x.inspections=[*(x.inspections or []),record];audit(s,u,'pellet_measured',str(x.blend_id)+' / '+x.state);return x
def create_pellet(s,data,u):
    b=get(s,Blend,data.blend_id,True)
    if b.status!='released':raise HTTPException(409,'只有主管已放行投料配方可登记成品粒料')
    if s.scalar(select(PelletCheck.id).where(PelletCheck.blend_id==b.id)):raise HTTPException(409,'配方已登记粒料检验，请使用原记录复检')
    snap=view(s,b);snap['captured_at']=datetime.now(timezone.utc).isoformat();snap['supplier_trace']=[]
    for p in snap['portions']:
        link=s.scalar(select(LotBale).where(LotBale.bale_id==p['bale_id']))
        if link:
            lot=s.get(SupplierLot,link.lot_id);snap['supplier_trace'].append({'bale_id':p['bale_id'],'lot_code':lot.code,'supplier':lot.supplier,'state_at_sampling':lot.state})
        else:snap['supplier_trace'].append({'bale_id':p['bale_id'],'lot_code':None,'legacy_unassigned':True})
    x=PelletCheck(blend_id=b.id,input_snapshot=snap,inspections=[]);measure(s,x,data,u,'首次成品取样');s.add(x);s.flush();return pellet_view(s,x)
def retest(s,id,data,u):
    x=get(s,PelletCheck,id,True)
    if x.state!='quarantine':raise HTTPException(409,'只有隔离粒料可复检，已合格或签证记录不可改写')
    if len(data.reason.strip())<8:raise HTTPException(409,'复检须填写至少8字的处置依据')
    measure(s,x,data,u,data.reason.strip());return pellet_view(s,x)
def certify(s,id,u):
    x=get(s,PelletCheck,id,True)
    if x.state!='passed':raise HTTPException(409,'须PVC合格且未签证，隔离粒料不得发证')
    from .production_service import accepted_drying
    drying=accepted_drying(s,x.blend_id)
    x.certificate_code=f'HL-CERT-{x.id:06d}';x.certified_by=u['email'];x.state='certified'
    x.certificate_snapshot={'code':x.certificate_code,'certified_by':u['email'],'at':datetime.now(timezone.utc).isoformat(),'input':x.input_snapshot,'measurements':x.inspections[-1],'inspection_count':len(x.inspections),'drying':drying}
    audit(s,u,'pellet_certified',x.certificate_code);return pellet_view(s,x)
