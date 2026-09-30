from datetime import datetime, timezone
from sqlalchemy import String, Integer, Float, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base

def now(): return datetime.now(timezone.utc)

class Tenant(Base):                       # one row per client (multi-tenant SaaS)
    __tablename__ = "tenants"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    pack: Mapped[str] = mapped_column(String(80), default="hospitality_resort")
    plan: Mapped[str] = mapped_column(String(20), default="starter")

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), index=True)
    email: Mapped[str] = mapped_column(String(200), unique=True)
    pw_hash: Mapped[str] = mapped_column(String(300))
    role: Mapped[str] = mapped_column(String(20), default="viewer")   # admin | manager | viewer
    position_code: Mapped[str | None] = mapped_column(String(50), nullable=True)

class Position(Base):                     # "position, not person"
    __tablename__ = "positions"
    __table_args__ = (UniqueConstraint("tenant_id", "code"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), index=True)
    code: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(200))
    tier: Mapped[str] = mapped_column(String(50), default="")
    department: Mapped[str] = mapped_column(String(100), default="")
    reports_to: Mapped[str | None] = mapped_column(String(50), nullable=True)
    incumbent: Mapped[str | None] = mapped_column(String(200), nullable=True)  # optional, kept separate from the position

class KPI(Base):
    __tablename__ = "kpis"
    __table_args__ = (UniqueConstraint("tenant_id", "code"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), index=True)
    code: Mapped[str] = mapped_column(String(50))
    position_code: Mapped[str] = mapped_column(String(50))
    kra: Mapped[str] = mapped_column(String(200))
    name: Mapped[str] = mapped_column(String(300))
    unit: Mapped[str] = mapped_column(String(30), default="%")
    direction: Mapped[str] = mapped_column(String(10), default="higher")  # higher | lower
    target: Mapped[float] = mapped_column(Float)
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    frequency: Mapped[str] = mapped_column(String(20), default="monthly")

class ImportBatch(Base):                  # real audit trail of every admin upload
    __tablename__ = "import_batches"
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), index=True)
    filename: Mapped[str] = mapped_column(String(300))
    sha256: Mapped[str] = mapped_column(String(64))
    uploaded_by: Mapped[str] = mapped_column(String(200))
    rows_imported: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class Record(Base):                       # one row of evidence-backed actuals
    __tablename__ = "records"
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), index=True)
    kpi_code: Mapped[str] = mapped_column(String(50), index=True)
    period: Mapped[str] = mapped_column(String(20), index=True)           # e.g. 2026-Q3 or 2026-09
    actual: Mapped[float | None] = mapped_column(Float, nullable=True)
    evidence_ref: Mapped[str | None] = mapped_column(String(300), nullable=True)
    verifier: Mapped[str | None] = mapped_column(String(200), nullable=True)
    variance_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    corrective_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    institutionalized_as: Mapped[str | None] = mapped_column(String(300), nullable=True)  # SOP/training/control ref
    status: Mapped[str] = mapped_column(String(10), default="OPEN")       # OPEN | CLOSED
    batch_id: Mapped[int | None] = mapped_column(ForeignKey("import_batches.id"), nullable=True)
