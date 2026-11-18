from decimal import Decimal
from pydantic import BaseModel,Field
class Login(BaseModel):
    email:str
    password:str
class BaleIn(BaseModel):
    code:str=Field(min_length=2,max_length=60)
    kg:Decimal=Field(gt=0,le=100000,max_digits=12,decimal_places=3)
    melt_index:Decimal=Field(gt=0,le=200,max_digits=9,decimal_places=3)
    moisture:Decimal=Field(ge=0,le=100,max_digits=9,decimal_places=3)
    pvc_ppm:Decimal=Field(ge=0,le=10000,max_digits=9,decimal_places=3)
class BlendIn(BaseModel):
    code:str=Field(min_length=2,max_length=60)
    target_kg:Decimal=Field(gt=0,le=100000,max_digits=12,decimal_places=3)
    max_pvc:Decimal=Field(ge=0,le=10000,max_digits=9,decimal_places=3)
class PortionIn(BaseModel):
    bale_id:int
    kg:Decimal=Field(gt=0,le=100000,max_digits=12,decimal_places=3)
class PortionsIn(BaseModel):
    portions:list[PortionIn]=Field(max_length=50)
