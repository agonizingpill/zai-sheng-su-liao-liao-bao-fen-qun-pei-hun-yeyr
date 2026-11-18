from decimal import Decimal
from pydantic import BaseModel,Field
class LotIn(BaseModel):
    code:str=Field(min_length=2,max_length=60)
    supplier:str=Field(min_length=2,max_length=120)
    inspection_note:str=Field(min_length=8,max_length=600)
class BaleAssignment(BaseModel):
    bale_id:int=Field(gt=0)
class LotDecision(BaseModel):
    reason:str=Field(min_length=8,max_length=600)
class Measurements(BaseModel):
    actual_kg:Decimal=Field(gt=0,le=100000,max_digits=12,decimal_places=3)
    melt_index:Decimal=Field(gt=0,le=200,max_digits=9,decimal_places=3)
    pvc_ppm:Decimal=Field(ge=0,le=10000,max_digits=9,decimal_places=3)
class PelletIn(Measurements):
    blend_id:int=Field(gt=0)
class PelletRetest(Measurements):
    reason:str=Field(min_length=8,max_length=600)
