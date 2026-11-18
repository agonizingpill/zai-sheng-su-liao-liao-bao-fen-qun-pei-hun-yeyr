"""Supplier traceability and post-extrusion certificates have independent lifecycles."""
from decimal import Decimal
from sqlalchemy import String,Numeric,ForeignKey,JSON,CheckConstraint
from sqlalchemy.orm import Mapped,mapped_column
from .database import Base
class SupplierLot(Base):
    __tablename__='supplier_lots'
    id:Mapped[int]=mapped_column(primary_key=True)
    code:Mapped[str]=mapped_column(String(60),unique=True)
    supplier:Mapped[str]=mapped_column(String(120))
    inspection_note:Mapped[str]=mapped_column(String(600))
    state:Mapped[str]=mapped_column(String(20),default='active')
class LotBale(Base):
    __tablename__='lot_bales'
    id:Mapped[int]=mapped_column(primary_key=True)
    lot_id:Mapped[int]=mapped_column(ForeignKey('supplier_lots.id'))
    bale_id:Mapped[int]=mapped_column(ForeignKey('bales.id'),unique=True)
    received_snapshot:Mapped[dict]=mapped_column(JSON)
class PelletCheck(Base):
    __tablename__='pellet_checks'
    __table_args__=(CheckConstraint('actual_kg > 0 AND melt_index > 0 AND pvc_ppm >= 0'),)
    id:Mapped[int]=mapped_column(primary_key=True)
    blend_id:Mapped[int]=mapped_column(ForeignKey('blends.id'),unique=True)
    actual_kg:Mapped[Decimal]=mapped_column(Numeric(12,3))
    melt_index:Mapped[Decimal]=mapped_column(Numeric(9,3))
    pvc_ppm:Mapped[Decimal]=mapped_column(Numeric(9,3))
    state:Mapped[str]=mapped_column(String(20))
    input_snapshot:Mapped[dict]=mapped_column(JSON)
    inspections:Mapped[list]=mapped_column(JSON)
    certificate_code:Mapped[str|None]=mapped_column(String(60),unique=True,nullable=True)
    certified_by:Mapped[str|None]=mapped_column(String(120),nullable=True)
    certificate_snapshot:Mapped[dict|None]=mapped_column(JSON,nullable=True)
