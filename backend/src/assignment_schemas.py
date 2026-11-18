from pydantic import BaseModel,Field
class AssignIn(BaseModel):
    batch_key:str=Field(min_length=4,max_length=80)
    version:int=Field(gt=0)
    bale_ids:list[int]=Field(min_length=1,max_length=200)
