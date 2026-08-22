from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    policy_mode: Mapped[str] = mapped_column(String(32), default="balanced")
    locale: Mapped[str] = mapped_column(String(16), default="en")
    status: Mapped[str] = mapped_column(String(24), default="completed")
    llm_mode: Mapped[str] = mapped_column(String(24), default="fallback")
    at_risk_paise: Mapped[int] = mapped_column(Integer, default=0)
    recovered_paise: Mapped[int] = mapped_column(Integer, default=0)
    recommended_count: Mapped[int] = mapped_column(Integer, default=0)
    escalated_count: Mapped[int] = mapped_column(Integer, default=0)
    stopped_count: Mapped[int] = mapped_column(Integer, default=0)
    queued_count: Mapped[int] = mapped_column(Integer, default=0)
    policy_violations: Mapped[int] = mapped_column(Integer, default=0)
    degraded: Mapped[bool] = mapped_column(Boolean, default=False)

    cases: Mapped[list[Case]] = relationship(back_populates="run", cascade="all, delete-orphan")


class Case(Base):
    __tablename__ = "cases"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), index=True)
    event_id: Mapped[str] = mapped_column(String(64), index=True)
    payment_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    order_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_event: Mapped[str] = mapped_column(String(64))
    amount_paise: Mapped[int] = mapped_column(Integer, default=0)
    method: Mapped[str | None] = mapped_column(String(32), nullable=True)
    diagnosis_class: Mapped[str | None] = mapped_column(String(64), nullable=True)
    diagnosis_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    diagnosis_source: Mapped[str | None] = mapped_column(String(24), nullable=True)
    action: Mapped[str | None] = mapped_column(String(64), nullable=True)
    channel: Mapped[str | None] = mapped_column(String(32), nullable=True)
    outcome: Mapped[str | None] = mapped_column(String(32), nullable=True)
    recovered_paise: Mapped[int] = mapped_column(Integer, default=0)
    bucket: Mapped[str | None] = mapped_column(String(24), nullable=True)
    degraded: Mapped[bool] = mapped_column(Boolean, default=False)
    message_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    message_hinglish: Mapped[str | None] = mapped_column(Text, nullable=True)
    policy_reasons_json: Mapped[str] = mapped_column(Text, default="[]")
    revenue_json: Mapped[str] = mapped_column(Text, default="{}")
    raw_event_json: Mapped[str] = mapped_column(Text, default="{}")

    run: Mapped[Run] = relationship(back_populates="cases")
    audits: Mapped[list[AuditEntry]] = relationship(back_populates="case", cascade="all, delete-orphan")


class AuditEntry(Base):
    __tablename__ = "audit_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"), index=True)
    run_id: Mapped[str] = mapped_column(String(40), index=True)
    ts: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    actor: Mapped[str] = mapped_column(String(32))
    event_type: Mapped[str] = mapped_column(String(64))
    severity: Mapped[str] = mapped_column(String(16), default="info")
    payload_json: Mapped[str] = mapped_column(Text, default="{}")

    case: Mapped[Case] = relationship(back_populates="audits")


class SeenEvent(Base):
    __tablename__ = "seen_events"

    event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    case_id: Mapped[str] = mapped_column(String(40))
    seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class FaultConfig(Base):
    __tablename__ = "fault_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    llm: Mapped[str] = mapped_column(String(16), default="up")
    whatsapp: Mapped[str] = mapped_column(String(16), default="ok")
