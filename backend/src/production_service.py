from datetime import datetime,timezone
from zoneinfo import ZoneInfo
from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy import select,func
from .database import Session
from .models import Blend
from .quality_models import PelletCheck
from .production_models import Dryer,DryingRun,PelletPack,BlendShipment,ShipmentPack
from .blending import obj,get,audit,view

def stamp(v):return (v.replace(tzinfo=ZoneInfo('Asia/Shanghai'))if v.tzinfo is None else v).astimezone(timezone.utc)
def now():return datetime.now(timezone.utc).isoformat()
def dry_view(s,x):return {**obj(x),'blend_code':s.get(Blend,x.blend_id).code,'dryer_code':s.get(Dryer,x.dryer_id).code}
def pack_view(s,x):
    p=s.get(PelletCheck,x.check_id)
    return {**obj(x),'blend_code':s.get(Blend,p.blend_id).code,'certificate_code':p.certificate_code}
def ship_view(s,x):
    packs=[{**obj(link),'pack_code':s.get(PelletPack,link.pack_id).code}for link in s.scalars(select(ShipmentPack).where(ShipmentPack.shipment_id==x.id).order_by(ShipmentPack.id))]
    return {**obj(x),'packs':packs,'total_kg':float(sum((Decimal(str(p['pack_snapshot']['kg']))for p in packs),Decimal(0)))}
def room(s,dryer_id,start,end,exclude=None):
    for x in s.scalars(select(DryingRun).where(DryingRun.dryer_id==dryer_id).with_for_update().execution_options(populate_existing=True)):
        if x.id!=exclude and datetime.fromisoformat(x.starts_at)<end and datetime.fromisoformat(x.ends_at)>start:raise HTTPException(409,'烘干设备在此时段已有作业，不能重叠占用')
def create_dry(s,p,u):
    dryer=get(s,Dryer,p.dryer_id,True)
    if dryer.state!='active':raise HTTPException(409,'烘干设备已停用')
    blend=get(s,Blend,p.blend_id,True)
    if blend.status!='released':raise HTTPException(409,'只有已投料配方可安排烘干')
    if s.scalar(select(DryingRun.id).where(DryingRun.blend_id==blend.id)):raise HTTPException(409,'配方已有烘干作业，需在原单延烘复测')
    start,end=stamp(p.starts_at),stamp(p.ends_at)
    if end<=start:raise HTTPException(409,'烘干结束须晚于开始')
    room(s,dryer.id,start,end);snap=view(s,blend);weight=sum(Decimal(str(x['kg']))for x in snap['portions'])
    moisture=sum(Decimal(str(x['kg']))*Decimal(str(x['moisture_snapshot']))for x in snap['portions'])/weight
    x=DryingRun(blend_id=blend.id,dryer_id=dryer.id,input_moisture=moisture.quantize(Decimal('.0001')),starts_at=start.isoformat(),ends_at=end.isoformat(),state='drying',measurements=[],input_snapshot=snap);s.add(x);s.flush();audit(s,u,'drying_started',blend.code);return dry_view(s,x)
def measure_dry(s,id,p,u):
    candidate=get(s,DryingRun,id);get(s,Dryer,candidate.dryer_id,True);x=get(s,DryingRun,id,True)
    if x.state not in ('drying','redry'):raise HTTPException(409,'仅烘干中或待延烘可复测，合格或已验收结果冻结')
    end=stamp(p.ends_at)
    if end<datetime.fromisoformat(x.ends_at):raise HTTPException(409,'延烘复测结束时间不得早于已占用结束时间')
    room(s,x.dryer_id,datetime.fromisoformat(x.starts_at),end,x.id)
    x.ends_at=end.isoformat();x.after_moisture=p.after_moisture;x.state='passed'if p.after_moisture<=Decimal('.05')else'redry'
    x.measurements=[*x.measurements,{'after_moisture':float(p.after_moisture),'ends_at':x.ends_at,'note':p.note,'actor':u['email'],'at':now()}];audit(s,u,'drying_measured',str(x.id)+' / '+x.state);return dry_view(s,x)
def accept_dry(s,id,u):
    x=get(s,DryingRun,id,True)
    if x.state!='passed':raise HTTPException(409,'烘后含水须≤0.05%且未验收，才能主管确认')
    x.state='accepted';x.accepted_by=u['email'];audit(s,u,'drying_accepted',str(x.id));return dry_view(s,x)
def accepted_drying(s,blend_id):
    x=s.scalar(select(DryingRun).where(DryingRun.blend_id==blend_id,DryingRun.state=='accepted'))
    if not x:raise HTTPException(409,'成品新签证须有同配方主管验收合格的烘干作业')
    return dry_view(s,x)
def available_pack_weight(s,p,kg,exclude=None):
    used=sum((x.kg for x in s.scalars(select(PelletPack).where(PelletPack.check_id==p.id,PelletPack.state!='cancelled').with_for_update().execution_options(populate_existing=True))if x.id!=exclude),Decimal(0))
    if used+kg>p.actual_kg:raise HTTPException(409,'累计有效包装重量超过合格粒料产出，不分配超额箱码')
def create_pack(s,p,u):
    check=get(s,PelletCheck,p.check_id,True)
    if check.state!='certified':raise HTTPException(409,'仅主管已发合格证的成品可以包装')
    available_pack_weight(s,check,p.kg);x=PelletPack(**p.model_dump(),state='open',certificate_snapshot=check.certificate_snapshot);s.add(x);s.flush();audit(s,u,'pack_created',x.code);return pack_view(s,x)
def change_pack(s,id,p,u):
    candidate=get(s,PelletPack,id);check=get(s,PelletCheck,candidate.check_id,True);x=get(s,PelletPack,id,True)
    if x.state!='open':raise HTTPException(409,'只有未封包装可改重量，封包与出库后冻结')
    available_pack_weight(s,check,p.kg,x.id);x.kg=p.kg;audit(s,u,'pack_reweighed',x.code);return pack_view(s,x)
def pack_action(s,id,u,target):
    candidate=get(s,PelletPack,id);get(s,PelletCheck,candidate.check_id,True);x=get(s,PelletPack,id,True)
    if x.state!='open':raise HTTPException(409,'仅未封包装可封包或取消，不可重复')
    x.state=target;audit(s,u,'pack_'+target,x.code);return pack_view(s,x)
def load_pack(s,id,p,u):
    sh=get(s,BlendShipment,id,True)
    if sh.state!='loading':raise HTTPException(409,'发车后清单冻结，不能继续装车')
    pack=get(s,PelletPack,p.pack_id,True)
    if pack.state!='sealed':raise HTTPException(409,'只有已封箱且未装车箱码可装入清单')
    if s.scalar(select(ShipmentPack.id).where(ShipmentPack.pack_id==pack.id)):raise HTTPException(409,'箱码已装车，不得重复出库')
    check=get(s,PelletCheck,pack.check_id)
    for link in s.scalars(select(ShipmentPack).where(ShipmentPack.shipment_id==sh.id)):
        previous=get(s,PelletCheck,get(s,PelletPack,link.pack_id).check_id)
        if previous.blend_id!=check.blend_id:raise HTTPException(409,'同一车次只允许同配方成品，不可跨配方混装')
    s.add(ShipmentPack(shipment_id=sh.id,pack_id=pack.id,pack_snapshot=pack_view(s,pack)));pack.state='loaded';s.flush();audit(s,u,'shipment_loaded',sh.code+' / '+pack.code);return ship_view(s,sh)
def dispatch(s,id,u):
    sh=get(s,BlendShipment,id,True)
    if sh.state!='loading':raise HTTPException(409,'仅装车中清单可发车，不可重复出库')
    snap=ship_view(s,sh)
    if not snap['packs']:raise HTTPException(409,'清单没有已封箱成品，不能发车')
    sh.manifest={'code':sh.code,'customer':sh.customer,'packs':snap['packs'],'total_kg':snap['total_kg'],'at':now(),'dispatched_by':u['email']};sh.dispatched_by=u['email'];sh.state='dispatched';audit(s,u,'shipment_dispatched',sh.code);return ship_view(s,sh)
def receive(s,id,p,u):
    sh=get(s,BlendShipment,id,True)
    if sh.state!='dispatched':raise HTTPException(409,'仅已发车清单可签收，不能重复')
    manifest_kg=Decimal(str(sh.manifest['total_kg']));variance=(p.received_kg-manifest_kg)/manifest_kg*100
    if abs(variance)>Decimal('.5')and len(p.difference_note.strip())<8:raise HTTPException(409,'签收重量与清单偏差超过0.5%，须至少8字差异说明')
    sh.receipt_snapshot={**p.model_dump(mode='json'),'manifest_kg':float(manifest_kg),'variance_pct':float(variance.quantize(Decimal('.0001'))),'at':now(),'recorded_by':u['email']};sh.state='received';audit(s,u,'shipment_received',sh.code);return ship_view(s,sh)
