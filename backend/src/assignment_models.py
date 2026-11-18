"""Published cluster versions keep their assignment basis so new bales join without retraining."""
from sqlalchemy import String,BigInteger,Integer,Float,ForeignKey,JSON
from sqlalchemy.orm import Mapped,mapped_column
from .database import Base
class ClusterModel(Base):
    __tablename__='cluster_models'
    id:Mapped[int]=mapped_column(primary_key=True)
    version:Mapped[int]=mapped_column(BigInteger,unique=True)
    artifact:Mapped[dict]=mapped_column(JSON)
    trained_bales:Mapped[list]=mapped_column(JSON)
    metrics:Mapped[dict]=mapped_column(JSON)
    created_at:Mapped[str]=mapped_column(String(40))
class ClusterMeta(Base):
    __tablename__='cluster_meta'
    id:Mapped[int]=mapped_column(primary_key=True)
    current_version:Mapped[int|None]=mapped_column(BigInteger,nullable=True)
class AssignBatch(Base):
    __tablename__='assign_batches'
    id:Mapped[int]=mapped_column(primary_key=True)
    batch_key:Mapped[str]=mapped_column(String(80),unique=True)
    version:Mapped[int|None]=mapped_column(BigInteger,nullable=True)
    state:Mapped[str]=mapped_column(String(20))
    reason:Mapped[str]=mapped_column(String(600),default='')
    created_at:Mapped[str]=mapped_column(String(40))
class BaleAssignment(Base):
    __tablename__='bale_assignments'
    id:Mapped[int]=mapped_column(primary_key=True)
    batch_id:Mapped[int]=mapped_column(ForeignKey('assign_batches.id'))
    bale_id:Mapped[int]=mapped_column(ForeignKey('bales.id'))
    version:Mapped[int|None]=mapped_column(BigInteger,nullable=True)
    cluster_id:Mapped[int]=mapped_column(Integer)
    distance:Mapped[float]=mapped_column(Float)
    threshold:Mapped[float]=mapped_column(Float)
    state:Mapped[str]=mapped_column(String(20))
    reason:Mapped[str]=mapped_column(String(600),default='')
    created_at:Mapped[str]=mapped_column(String(40))
