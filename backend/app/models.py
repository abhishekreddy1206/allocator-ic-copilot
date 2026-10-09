"""Relational identities and immutable evaluation records; metadata uses JSONB."""

from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import String, Float, Integer, Boolean, DateTime, Text, ForeignKey, UniqueConstraint, LargeBinary
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def uid() -> str:
    return str(uuid4())


def now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Upload(Base):
    __tablename__ = "uploads"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    filename: Mapped[str] = mapped_column(String)
    sha256: Mapped[str] = mapped_column(String, unique=True)
    raw_csv: Mapped[str] = mapped_column(Text)
    original_file: Mapped[bytes | None] = mapped_column(LargeBinary)
    source_metadata: Mapped[dict | None] = mapped_column(JSONB)
    summary: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Fund(Base):
    __tablename__ = "funds"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    canonical_name: Mapped[str] = mapped_column(String)
    external_identifier: Mapped[str] = mapped_column(String, unique=True)
    manager_name: Mapped[str] = mapped_column(String)
    strategy: Mapped[str] = mapped_column(String, index=True)
    liquidity: Mapped[str] = mapped_column(String)
    management_fee: Mapped[float | None] = mapped_column(Float)
    performance_fee: Mapped[float | None] = mapped_column(Float)
    qualitative_notes: Mapped[str] = mapped_column(Text)
    source_file: Mapped[str] = mapped_column(ForeignKey("uploads.id"))
    source_row: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class MonthlyReturn(Base):
    __tablename__ = "monthly_returns"
    __table_args__ = (UniqueConstraint("fund_id", "period"),)
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    fund_id: Mapped[str] = mapped_column(ForeignKey("funds.id"), index=True)
    period: Mapped[str] = mapped_column(String(7), index=True)
    return_value: Mapped[float] = mapped_column(Float)
    source_file: Mapped[str] = mapped_column(ForeignKey("uploads.id"))
    source_row: Mapped[int] = mapped_column(Integer)
    normalization_metadata: Mapped[dict] = mapped_column(JSONB)


class DataQualityIssue(Base):
    __tablename__ = "data_quality_issues"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    severity: Mapped[str] = mapped_column(String)
    issue_type: Mapped[str] = mapped_column(String, index=True)
    fund_id: Mapped[str | None] = mapped_column(ForeignKey("funds.id"))
    source_file: Mapped[str] = mapped_column(ForeignKey("uploads.id"))
    source_row: Mapped[int | None] = mapped_column(Integer)
    description: Mapped[str] = mapped_column(Text)
    inferred_resolution: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String, default="open")


class BenchmarkReturn(Base):
    __tablename__ = "benchmark_returns"
    __table_args__ = (UniqueConstraint("symbol", "period"),)
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    symbol: Mapped[str] = mapped_column(String, index=True)
    period: Mapped[str] = mapped_column(String(7))
    return_value: Mapped[float] = mapped_column(Float)
    lineage: Mapped[dict] = mapped_column(JSONB)


class FactorReturn(Base):
    __tablename__ = "factor_returns"
    __table_args__ = (UniqueConstraint("factor", "period"),)
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    factor: Mapped[str] = mapped_column(String)
    period: Mapped[str] = mapped_column(String(7))
    return_value: Mapped[float] = mapped_column(Float)
    lineage: Mapped[dict] = mapped_column(JSONB)


class MacroObservation(Base):
    __tablename__ = "macro_observations"
    __table_args__ = (UniqueConstraint("series_id", "period"),)
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    series_id: Mapped[str] = mapped_column(String)
    period: Mapped[str] = mapped_column(String(7))
    value: Mapped[float] = mapped_column(Float)
    lineage: Mapped[dict] = mapped_column(JSONB)


class Mandate(Base):
    __tablename__ = "mandates"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String)
    parameters: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Run(Base):
    __tablename__ = "runs"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    mandate_id: Mapped[str] = mapped_column(ForeignKey("mandates.id"))
    result: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class MetricSnapshot(Base):
    __tablename__ = "metric_snapshots"
    __table_args__ = (UniqueConstraint("fund_id", "run_id"),)
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    fund_id: Mapped[str] = mapped_column(ForeignKey("funds.id"))
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), index=True)
    evaluation_period: Mapped[str] = mapped_column(String)
    observation_count: Mapped[int] = mapped_column(Integer)
    metrics: Mapped[dict] = mapped_column(JSONB)
    methodology: Mapped[dict] = mapped_column(JSONB)


class FactorExposure(Base):
    __tablename__ = "factor_exposures"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    fund_id: Mapped[str] = mapped_column(ForeignKey("funds.id"))
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"))
    factor_name: Mapped[str] = mapped_column(String)
    beta: Mapped[float] = mapped_column(Float)
    t_stat: Mapped[float | None] = mapped_column(Float)
    methodology_metadata: Mapped[dict] = mapped_column(JSONB)


class Evaluation(Base):
    __tablename__ = "evaluations"
    __table_args__ = (UniqueConstraint("fund_id", "run_id"),)
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    fund_id: Mapped[str] = mapped_column(ForeignKey("funds.id"))
    mandate_id: Mapped[str] = mapped_column(ForeignKey("mandates.id"))
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), index=True)
    eligible: Mapped[bool] = mapped_column(Boolean)
    failed_constraints: Mapped[list] = mapped_column(JSONB)
    component_scores: Mapped[dict] = mapped_column(JSONB)
    total_score: Mapped[float | None] = mapped_column(Float)
    rank: Mapped[int | None] = mapped_column(Integer)


class Evidence(Base):
    __tablename__ = "evidence"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), index=True)
    type: Mapped[str] = mapped_column(String, index=True)
    label: Mapped[str] = mapped_column(String)
    value: Mapped[dict] = mapped_column(JSONB)
    unit: Mapped[str] = mapped_column(String)
    source: Mapped[str] = mapped_column(String)
    source_identifier: Mapped[str] = mapped_column(String)
    observation_period: Mapped[str] = mapped_column(String)
    methodology: Mapped[str] = mapped_column(Text)
    provenance: Mapped[dict] = mapped_column(JSONB)
    live_or_cached: Mapped[str] = mapped_column(String)


class Memo(Base):
    __tablename__ = "memos"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), index=True)
    mandate_id: Mapped[str] = mapped_column(ForeignKey("mandates.id"))
    kind: Mapped[str] = mapped_column(String)
    recommendation: Mapped[str | None] = mapped_column(String)
    structured_sections: Mapped[dict] = mapped_column(JSONB)
    model_metadata: Mapped[dict] = mapped_column(JSONB)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class MemoClaim(Base):
    __tablename__ = "memo_claims"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    memo_id: Mapped[str] = mapped_column(ForeignKey("memos.id"), index=True)
    text: Mapped[str] = mapped_column(Text)
    claim_type: Mapped[str] = mapped_column(String)
    confidence: Mapped[str] = mapped_column(String)
    evidence_ids: Mapped[list] = mapped_column(JSONB)
