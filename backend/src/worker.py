import os,time,json
from pathlib import Path
from redis import Redis
from sqlalchemy import select
from .database import Session
from .models import Bale
from .clustering import cluster
r=Redis.from_url(os.getenv('REDIS_URL','redis://redis:6379/0'),decode_responses=True)
while True:
    Path('/artifacts/poly-heartbeat').write_text(str(time.time()))
    job=r.blpop('poly-cluster',timeout=2)
    if not job:continue
    try:
        with Session.begin() as s:
            bales=s.scalars(select(Bale).order_by(Bale.id).with_for_update()).all()
            labels,result=cluster(bales);version=int(time.time()*1000)
            for b,label in zip(bales,labels):b.cluster_id=label;b.cluster_version=version
            result['version']=version
        Path('/artifacts/clusters.json').write_text(json.dumps(result,ensure_ascii=False));r.set('poly-cluster-result',json.dumps(result,ensure_ascii=False));r.set('poly-cluster-state','complete')
    except Exception as e:r.set('poly-cluster-state','failed');r.set('poly-cluster-error',str(e))
    finally:r.delete('poly-cluster-lock')
