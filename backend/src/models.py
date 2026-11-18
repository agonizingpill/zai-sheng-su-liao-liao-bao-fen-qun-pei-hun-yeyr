from decimal import Decimal
from sqlalchemy import String,Numeric,ForeignKey,UniqueConstraint,CheckConstraint,Text,Integer,BigInteger
from sqlalchemy.orm import Mapped,mapped_column
from .database import Base
class User(Base):
    __tablename__='users'
    id:Mapped[int]=mapped_column(primary_key=True)
    email:Mapped[str]=mapped_column(String(120),unique=True)
    password:Mapped[str]=mapped_column(String(256))
    role:Mapped[str]=mapped_column(String(20))
class Bale(Base):
    __tablename__='bales'
    __table_args__=(CheckConstraint('kg > 0 AND available_kg >= 0 AND available_kg <= kg'),CheckConstraint('melt_index > 0 AND moisture >= 0 AND pvc_ppm >= 0'))
    id:Mapped[int]=mapped_column(primary_key=True)
    code:Mapped[str]=mapped_column(String(60),unique=True)
    kg:Mapped[Decimal]=mapped_column(Numeric(12,3))
    available_kg:Mapped[Decimal]=mapped_column(Numeric(12,3))
    melt_index:Mapped[Decimal]=mapped_column(Numeric(9,3))
    moisture:Mapped[Decimal]=mapped_column(Numeric(9,3))
    pvc_ppm:Mapped[Decimal]=mapped_column(Numeric(9,3))
    cluster_id:Mapped[int|None]=mapped_column(Integer,nullable=True)
    cluster_version:Mapped[int|None]=mapped_column(BigInteger,nullable=True)
class Blend(Base):
    __tablename__='blends'
    __table_args__=(CheckConstraint('target_kg > 0 AND max_pvc >= 0'),)
    id:Mapped[int]=mapped_column(primary_key=True)
    code:Mapped[str]=mapped_column(String(60),unique=True)
    target_kg:Mapped[Decimal]=mapped_column(Numeric(12,3))
    max_pvc:Mapped[Decimal]=mapped_column(Numeric(9,3))
    status:Mapped[str]=mapped_column(String(20),default='draft')
    weighted_pvc:Mapped[Decimal|None]=mapped_column(Numeric(9,3),nullable=True)
    released_by:Mapped[str]=mapped_column(String(120),default='')
class BlendPortion(Base):
    __tablename__='blend_portions'
    __table_args__=(UniqueConstraint('blend_id','bale_id'),CheckConstraint('kg > 0'))
    id:Mapped[int]=mapped_column(primary_key=True)
    blend_id:Mapped[int]=mapped_column(ForeignKey('blends.id'))
    bale_id:Mapped[int]=mapped_column(ForeignKey('bales.id'))
    kg:Mapped[Decimal]=mapped_column(Numeric(12,3))
    cluster_snapshot:Mapped[int]
    version_snapshot:Mapped[int]=mapped_column(BigInteger)
    pvc_snapshot:Mapped[Decimal]=mapped_column(Numeric(9,3))
    melt_snapshot:Mapped[Decimal]=mapped_column(Numeric(9,3))
    moisture_snapshot:Mapped[Decimal]=mapped_column(Numeric(9,3))
class Audit(Base):
    __tablename__='audit'
    id:Mapped[int]=mapped_column(primary_key=True)
    actor:Mapped[str]=mapped_column(String(120))
    action:Mapped[str]=mapped_column(String(60))
    detail:Mapped[str]=mapped_column(Text)
    at:Mapped[str]=mapped_column(String(40))
