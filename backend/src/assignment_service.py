from datetime import datetime,timezone
from sqlalchemy import select
from .models import Bale
from .assignment_models import ClusterModel,ClusterMeta,AssignBatch,BaleAssignment
from .blending import obj,audit
from .clustering import assign_points

def now():return datetime.now(timezone.utc).isoformat()

def published(s,lock=False):
    q=select(ClusterMeta).where(ClusterMeta.id==1)
    if lock:q=q.with_for_update()
    return s.scalar(q)

def batch_view(s,batch):
    items=s.scalars(select(BaleAssignment).where(BaleAssignment.batch_id==batch.id).order_by(BaleAssignment.id)).all()
    return {**obj(batch),'items':[{**obj(x),'bale_code':s.get(Bale,x.bale_id).code}for x in items]}

def run_batch(s,data,u):
    existing=s.scalar(select(AssignBatch).where(AssignBatch.batch_key==data.batch_key))
    if existing:return batch_view(s,existing)
    ids=sorted(set(data.bale_ids))
    bales={b.id:b for b in s.scalars(select(Bale).where(Bale.id.in_(ids)).order_by(Bale.id).with_for_update().execution_options(populate_existing=True))}
    meta=published(s,True)
    version=meta.current_version if meta else None
    def void(reason):
        batch=AssignBatch(batch_key=data.batch_key,version=version,state='voided',reason=reason,created_at=now())
        s.add(batch);s.flush()
        audit(s,u,'assign_voided',f'{data.batch_key} / {reason}')
        return batch_view(s,batch)
    if version is None:return void('尚无已发布分群版本，请先重新分群')
    if version!=data.version:return void(f'分群版本已切换为{version}，本批判定依据失效，原群号保留')
    model=s.scalar(select(ClusterModel).where(ClusterModel.version==version))
    if not model or not model.artifact:return void('该版本缺少留存的标准化参数与群中心，拒绝以当前全场补造')
    missing=[i for i in ids if i not in bales]
    if missing:return void('料包不存在：'+','.join(str(i)for i in missing))
    for b in bales.values():
        if b.cluster_id is not None:return void(f'{b.code}已并发归群或换版，整批作废且原群号保留')
    batch=AssignBatch(batch_key=data.batch_key,version=version,state='applied',reason='',created_at=now())
    s.add(batch);s.flush()
    rows=[[float(b.melt_index),float(b.moisture),float(b.pvc_ppm)]for b in(bales[i]for i in ids)]
    for b,(c,d,t)in zip((bales[i]for i in ids),assign_points(model.artifact,rows)):
        if d<=t:state='assigned';b.cluster_id=c;b.cluster_version=version;reason=f'距离{d:.4f}≤群{c+1}训练半径{t:.4f}'
        else:state='pending_recheck';reason=f'距离{d:.4f}超出群{c+1}训练半径{t:.4f}，待补检后重判'
        s.add(BaleAssignment(batch_id=batch.id,bale_id=b.id,version=version,cluster_id=c,distance=d,threshold=t,state=state,reason=reason,created_at=now()))
    audit(s,u,'assign_applied',f'{data.batch_key} / {len(ids)}包 / 版本{version}')
    s.flush()
    return batch_view(s,batch)

def page(s):
    meta=published(s)
    version=meta.current_version if meta else None
    model=s.scalar(select(ClusterModel).where(ClusterModel.version==version))if version else None
    unassigned=s.scalars(select(Bale).where(Bale.cluster_id.is_(None)).order_by(Bale.id)).all()
    latest={}
    if unassigned:
        for x in s.scalars(select(BaleAssignment).where(BaleAssignment.bale_id.in_([b.id for b in unassigned])).order_by(BaleAssignment.id)):latest[x.bale_id]=x
    def row(b):
        rec=latest.get(b.id)
        return{**obj(b),'last_assignment':obj(rec)if rec and rec.state=='pending_recheck'else None}
    batches=s.scalars(select(AssignBatch).order_by(AssignBatch.id.desc()).limit(20)).all()
    return{'current_version':version,'artifact_available':bool(model and model.artifact),'artifact':model.artifact if model else None,'trained_count':len(model.trained_bales)if model else 0,'metrics':model.metrics if model else None,'unassigned':[row(b)for b in unassigned],'batches':[batch_view(s,b)for b in batches]}
