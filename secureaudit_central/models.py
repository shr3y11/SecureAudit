"""Portable persistence models; no scanner commands are stored or executed."""
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def now():
    return datetime.now(timezone.utc).isoformat()


def uid():
    return str(uuid4())


class Base(DeclarativeBase):
    pass


class Endpoint(Base):
    __tablename__ = "central_endpoints"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    hostname: Mapped[str] = mapped_column(String(100), unique=True)
    group_name: Mapped[str] = mapped_column(String(100), default="Unassigned")
    platform: Mapped[str] = mapped_column(String(100), default="Windows")
    simulated: Mapped[bool] = mapped_column(Boolean, default=False)
    registered_at: Mapped[str] = mapped_column(String(40), default=now)
    last_seen: Mapped[str | None] = mapped_column(String(40), nullable=True)


class Assessment(Base):
    __tablename__ = "central_assessments"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    endpoint_id: Mapped[str] = mapped_column(ForeignKey("central_endpoints.id"), index=True)
    submission_id: Mapped[str] = mapped_column(String(100), unique=True)
    collected_at: Mapped[str] = mapped_column(String(40))
    received_at: Mapped[str] = mapped_column(String(40), default=now)
    evidence_json: Mapped[str] = mapped_column(Text)
    sha256: Mapped[str] = mapped_column(String(64))
    source: Mapped[str] = mapped_column(String(30), default="imported")
    passed: Mapped[int] = mapped_column(Integer)
    failed: Mapped[int] = mapped_column(Integer)
    errors: Mapped[int] = mapped_column(Integer)


class Job(Base):
    __tablename__ = "central_jobs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    endpoint_id: Mapped[str] = mapped_column(ForeignKey("central_endpoints.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="queued", index=True)
    kind: Mapped[str] = mapped_column(String(20), default="demo")
    created_at: Mapped[str] = mapped_column(String(40), default=now)
    due_at: Mapped[str] = mapped_column(String(40))
    completed_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    assessment_id: Mapped[str | None] = mapped_column(ForeignKey("central_assessments.id"), nullable=True)


class Event(Base):
    __tablename__ = "central_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    at: Mapped[str] = mapped_column(String(40), default=now, index=True)
    action: Mapped[str] = mapped_column(String(100))
    detail: Mapped[str] = mapped_column(String(500))
