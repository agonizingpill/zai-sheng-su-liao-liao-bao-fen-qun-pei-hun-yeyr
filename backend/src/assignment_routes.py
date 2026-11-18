from fastapi import APIRouter,Depends
from .database import Session
from .security import current,allow
from .assignment_schemas import AssignIn
from . import assignment_service as svc
router=APIRouter()
@router.get('/assignments')
def page(u=Depends(current)):
    with Session() as s:return svc.page(s)
@router.post('/assignments')
def run(p:AssignIn,u=Depends(current)):
    allow(u,'admin','blender')
    with Session.begin() as s:return svc.run_batch(s,p,u)
