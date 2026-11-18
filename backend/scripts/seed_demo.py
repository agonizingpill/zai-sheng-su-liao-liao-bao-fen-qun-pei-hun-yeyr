import random,json
from decimal import Decimal
from sqlalchemy import select,func
from src.database import Base,engine,Session
from src.models import User,Bale,Blend,BlendPortion
from src.quality_models import SupplierLot,LotBale,PelletCheck
from src.blending import obj
from src.production_models import Dryer,DryingRun,PelletPack,BlendShipment,ShipmentPack
from src.security import password_hash

def seed():
    Base.metadata.create_all(engine)
    with Session.begin() as s:
        for role in ['admin','blender','viewer']:
            if not s.scalar(select(User).where(User.email==role+'@huanli.local')):s.add(User(email=role+'@huanli.local',password=password_hash('Blend2026!'),role=role))
        rng=random.Random(42)
        for i in range(45):
            code=f'PET-{117+i}'
            if s.scalar(select(Bale).where(Bale.code==code)):continue
            group=i//15
            melt=[9,27,49][group]+rng.uniform(-1.5,1.5);moist=[.12,.35,.7][group]+rng.uniform(-.025,.025);pvc=[18,70,180][group]+rng.uniform(-5,5)
            s.add(Bale(code=code,kg=Decimal('500'),available_kg=Decimal('500'),melt_index=Decimal(str(round(melt,3))),moisture=Decimal(str(round(moist,3))),pvc_ppm=Decimal(str(round(pvc,3)))))
        for code,target,limit in [('BL-20261117',400,40),('BL-LOW-PVC',400,5)]:
            if not s.scalar(select(Blend).where(Blend.code==code)):s.add(Blend(code=code,target_kg=target,max_pvc=limit,status='draft',released_by=''))
        for dryer_code in ('DRY-A','DRY-B'):
            if not s.scalar(select(Dryer).where(Dryer.code==dryer_code)):s.add(Dryer(code=dryer_code,state='active'))
        s.flush()
        for code,supplier,state,bale_code in [('SL-ACCEPT-17','澄江回收站','active','PET-129'),('SL-HOLD-17','河东塑料分选','quarantine','PET-131')]:
            lot=s.scalar(select(SupplierLot).where(SupplierLot.code==code))
            if not lot:
                lot=SupplierLot(code=code,supplier=supplier,state=state,inspection_note='来料标签与取样记录已核对，按批次状态暂存');s.add(lot);s.flush()
                bale=s.scalar(select(Bale).where(Bale.code==bale_code))
                if not s.scalar(select(LotBale.id).where(LotBale.bale_id==bale.id)):
                    s.add(LotBale(lot_id=lot.id,bale_id=bale.id,received_snapshot=obj(bale)))
    with Session() as s:print(json.dumps({k:s.scalar(select(func.count()).select_from(v)) for k,v in [('users',User),('bales',Bale),('blends',Blend),('portions',BlendPortion),('supplier_lots',SupplierLot),('lot_bales',LotBale),('pellet_checks',PelletCheck),('dryers',Dryer),('drying_runs',DryingRun),('packs',PelletPack),('shipments',BlendShipment),('shipment_packs',ShipmentPack)]}))
if __name__=='__main__':seed()
