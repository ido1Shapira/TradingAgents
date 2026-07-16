from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Column, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid.uuid4())


class WatchlistItem(Base):
    __tablename__ = "watchlist"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(20), unique=True, nullable=False, index=True)
    company_name = Column(String(200), default="")
    exchange = Column(String(50), default="")
    source = Column(String(50), default="user")
    sort_order = Column(Integer, default=0)
    group_name = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    last_run_id = Column(String(100), nullable=True)
    last_decision = Column(String(500), nullable=True)
    last_decision_at = Column(String(30), nullable=True)


class RunRecord(Base):
    __tablename__ = "runs"

    id = Column(String(100), primary_key=True)
    ticker = Column(String(20), nullable=False, index=True)
    date = Column(String(20), nullable=False)
    status = Column(String(20), default="queued")
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    summary = Column(Text, nullable=True)
    cancel_requested = Column(Integer, default=0)
    run_type = Column(String(20), default="manual")
    run_data = Column(JSON, nullable=True)


class RunEvent(Base):
    __tablename__ = "run_events"

    id = Column(String(36), primary_key=True, default=_uuid)
    run_id = Column(String(36), nullable=False, index=True)
    event_type = Column(String(50), nullable=False)
    data = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)


class LlmCallRecord(Base):
    __tablename__ = "llm_calls"

    id = Column(String(36), primary_key=True, default=_uuid)
    run_id = Column(String(36), nullable=False, index=True)
    provider = Column(String(50), nullable=True)
    model = Column(String(100), nullable=True)
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    duration_ms = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)


class Indicator(Base):
    __tablename__ = "indicators"

    id = Column(String(36), primary_key=True, default=_uuid)
    kind = Column(String(50), nullable=False)
    name = Column(String(100), nullable=True)
    threshold = Column(Float, nullable=True)
    description = Column(String(500), nullable=True)
    enabled = Column(Integer, default=1)
    ticker = Column(String(20), nullable=True)
    comparator = Column(String(10), nullable=True)
    triggered = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=_utcnow)


class IndicatorSchedule(Base):
    __tablename__ = "indicator_schedule"

    id = Column(Integer, primary_key=True, autoincrement=True)
    interval_ms = Column(Integer, default=0)
    last_check_at = Column(String(30), nullable=True)


class AppConfig(Base):
    __tablename__ = "app_config"

    key = Column(String(100), primary_key=True)
    value = Column(Text, nullable=True)


class NotifierConfig(Base):
    __tablename__ = "notifier_config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    enabled = Column(Integer, default=0)
    bot_token = Column(String(200), nullable=True)
    chat_id = Column(String(50), nullable=True)


class StageRecord(Base):
    __tablename__ = "stages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(100), nullable=False, index=True)
    stage = Column(String(50), nullable=False)
    data = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)


class BackgroundJob(Base):
    __tablename__ = "background_jobs"

    id = Column(String(36), primary_key=True, default=_uuid)
    ticker = Column(String(20), nullable=False)
    date_from = Column(String(20), nullable=False)
    date_to = Column(String(20), nullable=False)
    every = Column(String(10), default="1d")
    parallel = Column(Integer, default=1)
    status = Column(String(20), default="active")
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    last_run_at = Column(DateTime(timezone=True), nullable=True)
