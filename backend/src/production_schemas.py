from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel,Field,ConfigDict
class Clean(BaseModel):model_config=ConfigDict(str_strip_whitespace=True)
class DryerInput(Clean):code:str=Field(min_length=2,max_length=40)
class DryingInput(Clean):
    blend_id:int=Field(gt=0)
    dryer_id:int=Field(gt=0)
    starts_at:datetime
    ends_at:datetime
class DryingMeasure(Clean):
    after_moisture:Decimal=Field(ge=0,le=100,max_digits=9,decimal_places=4)
    ends_at:datetime
    note:str=Field(min_length=8,max_length=600)
class PackInput(Clean):
    check_id:int=Field(gt=0)
    code:str=Field(min_length=2,max_length=80)
    kg:Decimal=Field(gt=0,le=100000,max_digits=12,decimal_places=3)
class PackWeight(Clean):kg:Decimal=Field(gt=0,le=100000,max_digits=12,decimal_places=3)
class ShipmentInput(Clean):
    code:str=Field(min_length=2,max_length=70)
    customer:str=Field(min_length=2,max_length=120)
class LoadPack(Clean):pack_id:int=Field(gt=0)
class ShipmentReceipt(Clean):
    received_kg:Decimal=Field(gt=0,le=100000,max_digits=12,decimal_places=3)
    received_by:str=Field(min_length=2,max_length=120)
    difference_note:str=Field(default='',max_length=600)
