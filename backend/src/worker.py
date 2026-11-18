import os,time,json
from datetime import datetime,timezone
from pathlib import Path
from redis import Redis
from sqlalchemy import select
from .database import Session
from .models import Bale
from .assignment_models import ClusterModel,ClusterMeta
from .clustering import cluster
r=Redis.from_url(os.getenv('REDIS_URL','redis://redis:6379/0'),decode_responses=True)
while True:
    Path('/artifacts/poly-heartbeat').write_text(str(time.time()))
    job=r.blpop('poly-cluster',timeout=2)
    if not job:continue
    try:
        with Session.begin() as s:
            bales=s.scalars(select(Bale).order_by(Bale.id).with_for_update()).all()
            labels,result,artifact=cluster(bales)
            version=int(time.time()*1000)
            for b,label in zip(bales,labels):b.cluster_id=label;b.cluster_version=version
            trained=[{'id':b.id,'code':b.code,'melt_index':float(b.melt_index),'moisture':float(b.moisture),'pvc_ppm':float(b.pvc_ppm),'cluster':l}for b,l in zip(bales,labels)]
            s.add(ClusterModel(version=version,artifact=artifact,trained_bales=trained,metrics={'silhouette':result['silhouette'],'inertia':result['inertia'],'rows':result['rows']},created_at=datetime.now(timezone.utc).isoformat()))
            meta=s.scalar(select(ClusterMeta).where(ClusterMeta.id==1).with_for_update())
            if not meta:meta=ClusterMeta(id=1);s.add(meta)
            meta.current_version=version
            result['version']=version
        Path('/artifacts/clusters.json').write_text(json.dumps(result,ensure_ascii=False));r.set('poly-cluster-result',json.dumps(result,ensure_ascii=False));r.set('poly-cluster-state','complete')
    except Exception as e:r.set('poly-cluster-state','failed');r.set('poly-cluster-error',str(e))
    finally:r.delete('poly-cluster-lock')
