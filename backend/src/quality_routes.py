from fastapi import APIRouter,Depends
from sqlalchemy import select
from .database import Session
from .security import current,allow
from .quality_models import SupplierLot,PelletCheck
from .quality_schemas import LotIn,BaleAssignment,LotDecision,PelletIn,PelletRetest
from .blending import audit
from . import quality_service as svc
router=APIRouter()
@router.get('/supplier-lots')
def lots(u=Depends(current)):
    with Session() as s:return [svc.lot_view(s,x) for x in s.scalars(select(SupplierLot).order_by(SupplierLot.id.desc()))]
@router.post('/supplier-lots')
def create_lot(p:LotIn,u=Depends(current)):
    allow(u,'admin','blender')
    with Session.begin() as s:
        x=SupplierLot(**p.model_dump(),state='active');s.add(x);s.flush();audit(s,u,'lot_received',x.code);return svc.lot_view(s,x)
@router.post('/supplier-lots/{lid}/bales')
def assign(lid:int,p:BaleAssignment,u=Depends(current)):
    allow(u,'admin','blender')
    with Session.begin() as s:return svc.assign(s,lid,p,u)
@router.post('/supplier-lots/{lid}/quarantine')
def quarantine(lid:int,p:LotDecision,u=Depends(current)):
    allow(u,'admin')
    with Session.begin() as s:return svc.decide_lot(s,lid,p,u,'quarantine')
@router.post('/supplier-lots/{lid}/clear')
def clear(lid:int,p:LotDecision,u=Depends(current)):
    allow(u,'admin')
    with Session.begin() as s:return svc.decide_lot(s,lid,p,u,'active')
@router.get('/pellet-checks')
def pellets(u=Depends(current)):
    with Session() as s:return [svc.pellet_view(s,x) for x in s.scalars(select(PelletCheck).order_by(PelletCheck.id.desc()))]
@router.post('/pellet-checks')
def create_check(p:PelletIn,u=Depends(current)):
    allow(u,'admin','blender')
    with Session.begin() as s:return svc.create_pellet(s,p,u)
@router.post('/pellet-checks/{id}/retest')
def retest(id:int,p:PelletRetest,u=Depends(current)):
    allow(u,'admin','blender')
    with Session.begin() as s:return svc.retest(s,id,p,u)
@router.post('/pellet-checks/{id}/certify')
def certify(id:int,u=Depends(current)):
    allow(u,'admin')
    with Session.begin() as s:return svc.certify(s,id,u)
