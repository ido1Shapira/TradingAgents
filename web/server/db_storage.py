"""Database-backed storage for the TradingAgents dashboard.

Replaces file-based JSON storage with Postgres via SQLAlchemy async.
Designed as a drop-in replacement — each method mirrors a function in storage.py.
"""
from __future__ import annotations

import json
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from web.server.config import get_database_url
from web.server.models import (
    BackgroundJob,
    Indicator,
    IndicatorSchedule,
    LlmCallRecord,
    NotifierConfig,
    RunEvent,
    RunRecord,
    WatchlistItem,
)

log = logging.getLogger(__name__)

_engine = None
_session_factory = None


async def init_db() -> None:
    """Initialize the async engine and create tables if needed."""
    global _engine, _session_factory
    url = get_database_url()
    if not url:
        log.warning("No DATABASE_URL configured — DB storage unavailable")
        return
    _engine = create_async_engine(url, pool_size=5, max_overflow=10)
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)
    async with _engine.begin() as conn:
        from web.server.models import Base
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Dispose of the engine."""
    global _engine, _session_factory
    if _engine:
        await _engine.dispose()
        _engine = None
        _session_factory = None


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    if _session_factory is None:
        raise RuntimeError("DB not initialized — call init_db() first")
    async with _session_factory() as session:
        yield session


def is_available() -> bool:
    return _engine is not None


# ---- Watchlist ----

async def read_watchlist() -> list[dict]:
    if not is_available():
        return []
    async with get_session() as session:
        result = await session.execute(
            select(WatchlistItem).order_by(WatchlistItem.sort_order)
        )
        rows = result.scalars().all()
        return [_watchlist_to_dict(r) for r in rows]


async def add_ticker(
    ticker: str,
    company_name: str = "",
    exchange: str = "",
    source: str = "user",
    group: str | None = None,
) -> dict:
    async with get_session() as session:
        count = await session.scalar(select(func.count()).select_from(WatchlistItem))
        item = WatchlistItem(
            ticker=ticker.upper(),
            company_name=company_name,
            exchange=exchange,
            source=source,
            sort_order=(count or 0),
            group_name=group,
        )
        session.add(item)
        await session.commit()
        await session.refresh(item)
        return _watchlist_to_dict(item)


async def remove_ticker(ticker: str) -> None:
    async with get_session() as session:
        await session.execute(
            delete(WatchlistItem).where(WatchlistItem.ticker == ticker.upper())
        )
        await session.commit()


async def reorder_watchlist(tickers: list[str]) -> None:
    async with get_session() as session:
        for idx, t in enumerate(tickers):
            await session.execute(
                update(WatchlistItem)
                .where(WatchlistItem.ticker == t.upper())
                .values(sort_order=idx)
            )
        await session.commit()


async def update_watchlist_item(ticker: str, group: str | None = None) -> dict | None:
    async with get_session() as session:
        result = await session.execute(
            select(WatchlistItem).where(WatchlistItem.ticker == ticker.upper())
        )
        item = result.scalar_one_or_none()
        if item is None:
            return None
        if group is not None:
            item.group_name = group if group else None
        await session.commit()
        await session.refresh(item)
        return _watchlist_to_dict(item)


def _watchlist_to_dict(row: WatchlistItem) -> dict:
    return {
        "id": row.id,
        "ticker": row.ticker,
        "company_name": row.company_name,
        "exchange": row.exchange,
        "source": row.source,
        "sort_order": row.sort_order,
        "group": row.group_name,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


# ---- Runs ----

async def create_run(ticker: str, date_str: str) -> str:
    async with get_session() as session:
        run = RunRecord(ticker=ticker.upper(), date=date_str, status="queued")
        session.add(run)
        await session.commit()
        await session.refresh(run)
        return run.id


async def read_run(run_id: str) -> dict | None:
    async with get_session() as session:
        result = await session.execute(
            select(RunRecord).where(RunRecord.id == run_id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return _run_to_dict(row)


async def update_run_status(
    run_id: str,
    status: str | None = None,
    cancel_requested: bool | None = None,
    summary: str | None = None,
) -> None:
    async with get_session() as session:
        vals: dict[str, Any] = {}
        if status is not None:
            vals["status"] = status
            if status in ("completed", "failed", "cancelled"):
                vals["finished_at"] = datetime.now(timezone.utc)
        if cancel_requested is not None:
            vals["cancel_requested"] = 1 if cancel_requested else 0
        if summary is not None:
            vals["summary"] = summary
        if vals:
            await session.execute(
                update(RunRecord).where(RunRecord.id == run_id).values(**vals)
            )
            await session.commit()


async def list_ticker_runs(ticker: str, limit: int = 50) -> list[dict]:
    async with get_session() as session:
        result = await session.execute(
            select(RunRecord)
            .where(RunRecord.ticker == ticker.upper())
            .order_by(RunRecord.created_at.desc())
            .limit(limit)
        )
        return [_run_to_dict(r) for r in result.scalars().all()]


async def delete_run(run_id: str) -> bool:
    async with get_session() as session:
        result = await session.execute(
            delete(RunRecord).where(RunRecord.id == run_id)
        )
        await session.commit()
        return result.rowcount > 0


def _run_to_dict(row: RunRecord) -> dict:
    return {
        "id": row.id,
        "ticker": row.ticker,
        "date": row.date,
        "status": row.status,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "finished_at": row.finished_at.isoformat() if row.finished_at else None,
        "summary": row.summary,
        "cancel_requested": bool(row.cancel_requested),
        "run_type": row.run_type,
    }


# ---- Run Events ----

async def append_run_event(run_id: str, event: dict) -> str:
    async with get_session() as session:
        ev = RunEvent(
            run_id=run_id,
            event_type=event.get("type", "unknown"),
            data=json.dumps(event, ensure_ascii=False),
        )
        session.add(ev)
        await session.commit()
        await session.refresh(ev)
        return ev.id


async def list_run_events(run_id: str) -> list[dict]:
    async with get_session() as session:
        result = await session.execute(
            select(RunEvent)
            .where(RunEvent.run_id == run_id)
            .order_by(RunEvent.created_at)
        )
        out = []
        for ev in result.scalars().all():
            d = json.loads(ev.data) if ev.data else {}
            d["id"] = ev.id
            d["created_at"] = ev.created_at.isoformat() if ev.created_at else None
            out.append(d)
        return out


# ---- LLM Calls ----

async def append_llm_call(run_id: str, call: dict) -> str:
    async with get_session() as session:
        rec = LlmCallRecord(
            run_id=run_id,
            provider=call.get("provider"),
            model=call.get("model"),
            prompt_tokens=call.get("prompt_tokens"),
            completion_tokens=call.get("completion_tokens"),
            duration_ms=call.get("duration_ms"),
        )
        session.add(rec)
        await session.commit()
        await session.refresh(rec)
        return rec.id


async def list_run_llm_calls(run_id: str) -> list[dict]:
    async with get_session() as session:
        result = await session.execute(
            select(LlmCallRecord)
            .where(LlmCallRecord.run_id == run_id)
            .order_by(LlmCallRecord.created_at)
        )
        return [
            {
                "id": r.id,
                "run_id": r.run_id,
                "provider": r.provider,
                "model": r.model,
                "prompt_tokens": r.prompt_tokens,
                "completion_tokens": r.completion_tokens,
                "duration_ms": r.duration_ms,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in result.scalars().all()
        ]


# ---- Indicators ----

async def read_indicators() -> list[dict]:
    async with get_session() as session:
        result = await session.execute(
            select(Indicator).order_by(Indicator.created_at)
        )
        return [_indicator_to_dict(r) for r in result.scalars().all()]


async def add_indicator(data: dict) -> dict:
    async with get_session() as session:
        ind = Indicator(
            kind=data["kind"],
            name=data.get("name"),
            threshold=data.get("threshold"),
            description=data.get("description"),
            enabled=1 if data.get("enabled", True) else 0,
            ticker=data.get("ticker"),
            comparator=data.get("comparator"),
        )
        session.add(ind)
        await session.commit()
        await session.refresh(ind)
        return _indicator_to_dict(ind)


async def remove_indicator(indicator_id: str) -> bool:
    async with get_session() as session:
        result = await session.execute(
            delete(Indicator).where(Indicator.id == indicator_id)
        )
        await session.commit()
        return result.rowcount > 0


async def update_indicator(indicator_id: str, updates: dict) -> dict | None:
    async with get_session() as session:
        result = await session.execute(
            select(Indicator).where(Indicator.id == indicator_id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        for key, val in updates.items():
            if hasattr(row, key):
                setattr(row, key, val)
        await session.commit()
        await session.refresh(row)
        return _indicator_to_dict(row)


async def reset_indicators() -> list[dict]:
    async with get_session() as session:
        await session.execute(
            update(Indicator).values(triggered=0)
        )
        await session.commit()
        return await read_indicators()


async def reset_indicator(indicator_id: str) -> dict | None:
    async with get_session() as session:
        result = await session.execute(
            select(Indicator).where(Indicator.id == indicator_id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        row.triggered = 0
        await session.commit()
        await session.refresh(row)
        return _indicator_to_dict(row)


def _indicator_to_dict(row: Indicator) -> dict:
    return {
        "id": row.id,
        "kind": row.kind,
        "name": row.name,
        "threshold": row.threshold,
        "description": row.description,
        "enabled": bool(row.enabled),
        "ticker": row.ticker,
        "comparator": row.comparator,
        "triggered": bool(row.triggered),
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


# ---- Indicator Schedule ----

async def read_indicator_schedule() -> dict:
    async with get_session() as session:
        result = await session.execute(select(IndicatorSchedule).limit(1))
        row = result.scalar_one_or_none()
        if row is None:
            return {"interval_ms": 0, "last_check_at": None}
        return {
            "interval_ms": row.interval_ms,
            "last_check_at": row.last_check_at,
        }


async def write_indicator_schedule(data: dict) -> None:
    async with get_session() as session:
        result = await session.execute(select(IndicatorSchedule).limit(1))
        row = result.scalar_one_or_none()
        if row is None:
            row = IndicatorSchedule(
                interval_ms=data.get("interval_ms", 0),
                last_check_at=data.get("last_check_at"),
            )
            session.add(row)
        else:
            row.interval_ms = data.get("interval_ms", 0)
            if "last_check_at" in data:
                row.last_check_at = data["last_check_at"]
        await session.commit()


# ---- KV Config (generic key-value storage) ----

async def read_notifier_config() -> dict:
    async with get_session() as session:
        result = await session.execute(select(NotifierConfig).limit(1))
        row = result.scalar_one_or_none()
        if row is None:
            return {"enabled": False, "bot_token": None, "chat_id": None}
        return {
            "enabled": bool(row.enabled),
            "bot_token": row.bot_token,
            "chat_id": row.chat_id,
        }


async def write_notifier_config(cfg: dict) -> None:
    async with get_session() as session:
        result = await session.execute(select(NotifierConfig).limit(1))
        row = result.scalar_one_or_none()
        if row is None:
            row = NotifierConfig(
                enabled=1 if cfg.get("enabled") else 0,
                bot_token=cfg.get("bot_token"),
                chat_id=str(cfg.get("chat_id")) if cfg.get("chat_id") else None,
            )
            session.add(row)
        else:
            row.enabled = 1 if cfg.get("enabled") else 0
            row.bot_token = cfg.get("bot_token")
            row.chat_id = str(cfg.get("chat_id")) if cfg.get("chat_id") else None
        await session.commit()


# ---- Background Jobs ----

async def create_background_job(data: dict) -> str:
    async with get_session() as session:
        job = BackgroundJob(
            ticker=data["ticker"].upper(),
            date_from=data["date_from"],
            date_to=data["date_to"],
            every=data.get("every", "1d"),
            parallel=data.get("parallel", 1),
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)
        return job.id


async def list_background_jobs(limit: int = 50) -> list[dict]:
    async with get_session() as session:
        result = await session.execute(
            select(BackgroundJob)
            .order_by(BackgroundJob.created_at.desc())
            .limit(limit)
        )
        return [
            {
                "id": j.id,
                "ticker": j.ticker,
                "date_from": j.date_from,
                "date_to": j.date_to,
                "every": j.every,
                "parallel": j.parallel,
                "status": j.status,
                "created_at": j.created_at.isoformat() if j.created_at else None,
                "last_run_at": j.last_run_at.isoformat() if j.last_run_at else None,
            }
            for j in result.scalars().all()
        ]
