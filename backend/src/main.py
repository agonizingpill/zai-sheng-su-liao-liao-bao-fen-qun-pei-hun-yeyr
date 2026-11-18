import os,hmac,logging
from contextlib import asynccontextmanager
from fastapi import FastAPI,Depends,HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import select,text
from sqlalchemy.exc import IntegrityError
from redis import Redis
from .database import Base,engine,Session
from .models import User,Bale,Blend,BlendPortion,Audit
from .schemas import Login,BaleIn,BlendIn,PortionsIn
from .security import current,allow,password_hash,token_for
from .blending import obj,get,audit,view,set_portions,evaluate,release
from .middlewares import RequestTrace,Recovery
from scripts.seed_demo import seed
import json
logging.basicConfig(level=logging.INFO)
r=Redis.from_url(os.getenv('REDIS_URL','redis://redis:6379/0'),decode_responses=True)
@asynccontextmanager
async def lifespan(app):
    Base.metadata.create_all(engine)
    if os.getenv('SEED_DEMO','true')=='true':
        try:seed()
        except Exception:logging.exception('seed failed')
    yield
app=FastAPI(title='环粒 · 配混秤台',lifespan=lifespan);app.add_middleware(RequestTrace);app.add_middleware(Recovery)
from .quality_routes import router as quality_router
app.include_router(quality_router)
from .production_routes import router as production_router
app.include_router(production_router)
@app.exception_handler(IntegrityError)
async def duplicate(request,e):return JSONResponse({'detail':'编号已存在或关联数据不合法'},status_code=409)
@app.get('/health')
def health():
    with Session() as s:s.execute(text('SELECT 1'))
    return {'status':'ok','redis':r.ping()}
@app.post('/auth/login')
def login(d:Login):
    with Session() as s:
        u=s.scalar(select(User).where(User.email==d.email))
        if not u or not hmac.compare_digest(u.password,password_hash(d.password)):raise HTTPException(401,'账号或密码不正确')
        return {'token':token_for(u),'email':u.email,'role':u.role}
@app.get('/bales')
def bales(u=Depends(current)):
    with Session() as s:return [obj(x) for x in s.scalars(select(Bale).order_by(Bale.id))]
@app.post('/bales')
def add_bale(d:BaleIn,u=Depends(current)):
    allow(u,'admin','blender')
    with Session.begin() as s:
        x=Bale(**d.model_dump(),available_kg=d.kg);s.add(x);s.flush();audit(s,u,'bale_received',x.code);return obj(x)
@app.put('/bales/{id}')
def edit_bale(id:int,d:BaleIn,u=Depends(current)):
    allow(u,'admin','blender')
    with Session.begin() as s:
        b=get(s,Bale,id,True)
        if s.scalar(select(BlendPortion.id).where(BlendPortion.bale_id==id).limit(1)):raise HTTPException(409,'料包已被配方引用，质量与原始重量快照冻结')
        for k,v in d.model_dump().items():setattr(b,k,v)
        b.available_kg=d.kg;b.cluster_id=None;b.cluster_version=None;audit(s,u,'bale_retested',b.code);return obj(b)
@app.get('/clusters')
def clusters(u=Depends(current)):
    return {'status':r.get('poly-cluster-state') or 'idle','result':json.loads(r.get('poly-cluster-result') or 'null'),'error':r.get('poly-cluster-error')}
@app.post('/clusters/rebuild')
def rebuild(u=Depends(current)):
    allow(u,'admin','blender')
    if not r.set('poly-cluster-lock','1',nx=True,ex=120):raise HTTPException(409,'分群正在计算，请稍后查看')
    r.set('poly-cluster-state','queued');r.delete('poly-cluster-error');r.rpush('poly-cluster','all')
    return {'status':'queued'}
@app.get('/blends')
def blends(u=Depends(current)):
    with Session() as s:return [view(s,b) for b in s.scalars(select(Blend).order_by(Blend.id.desc()))]
@app.post('/blends')
def create_blend(d:BlendIn,u=Depends(current)):
    allow(u,'admin','blender')
    with Session.begin() as s:
        b=Blend(**d.model_dump(),status='draft',released_by='');s.add(b);s.flush();audit(s,u,'blend_created',b.code);return view(s,b)
@app.put('/blends/{id}/portions')
def weigh(id:int,d:PortionsIn,u=Depends(current)):
    allow(u,'admin','blender')
    with Session.begin() as s:return set_portions(s,get(s,Blend,id,True),d,u)
@app.post('/blends/{id}/check')
def check(id:int,u=Depends(current)):
    allow(u,'admin','blender')
    with Session.begin() as s:return evaluate(s,get(s,Blend,id,True),u)
@app.post('/blends/{id}/reopen')
def reopen(id:int,u=Depends(current)):
    allow(u,'admin','blender')
    with Session.begin() as s:
        b=get(s,Blend,id,True)
        if b.status!='ready':raise HTTPException(409,'仅待放行配方可退回，已放行配方不可改动')
        b.status='draft';b.weighted_pvc=None;audit(s,u,'blend_reopened',b.code);return view(s,b)
@app.post('/blends/{id}/release')
def release_blend(id:int,u=Depends(current)):
    allow(u,'admin')
    with Session.begin() as s:return release(s,get(s,Blend,id,True),u)
@app.get('/audit')
def audit_logs(u=Depends(current)):
    with Session() as s:return [obj(x) for x in s.scalars(select(Audit).order_by(Audit.id.desc()).limit(30))]
