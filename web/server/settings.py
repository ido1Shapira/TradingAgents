"""Environment-driven settings for the dashboard server."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _default_root() -> Path:
    return Path.home() / ".tradingagents"


@dataclass(frozen=True)
class Settings:
    data_dir: str = ""
    cache_dir: str = ""
    host: str = os.environ.get("TRADINGAGENTS_DASHBOARD_HOST", "127.0.0.1")
    port: int = int(os.environ.get("TRADINGAGENTS_DASHBOARD_PORT", "8000"))
    max_concurrent: int = int(os.environ.get("TRADINGAGENTS_DASHBOARD_MAX_CONCURRENT", "3"))
    price_poll_s: int = int(os.environ.get("TRADINGAGENTS_DASHBOARD_PRICE_POLL_S", "2"))
    log_level: str = os.environ.get("TRADINGAGENTS_DASHBOARD_LOG_LEVEL", "INFO")
    frontend_dist: str = os.environ.get("TRADINGAGENTS_FRONTEND_DIST", "web/frontend/dist")


def _resolve_data_dir() -> str:
    d = os.environ.get("TRADINGAGENTS_DATA_DIR")
    if d is not None:
        return d
    p = _default_root() / "data"
    p.parent.mkdir(parents=True, exist_ok=True)
    return str(p)


def _resolve_cache_dir() -> str:
    d = os.environ.get("TRADINGAGENTS_CACHE_DIR")
    if d is not None:
        return d
    p = _default_root() / "cache"
    p.parent.mkdir(parents=True, exist_ok=True)
    return str(p)


def get_settings() -> Settings:
    """Build Settings with env vars read AT CALL TIME (not class definition time).

    Class-level defaults are evaluated once when the module is imported, so
    monkeypatching TRADINGAGENTS_DATA_DIR after import has no effect on the
    default value. This factory re-reads os.environ each call so tests that
    set env vars in fixtures (and the conftest's monkeypatch) get isolated
    data dirs.
    """
    return Settings(
        data_dir=_resolve_data_dir(),
        cache_dir=_resolve_cache_dir(),
        host=os.environ.get("TRADINGAGENTS_DASHBOARD_HOST", "127.0.0.1"),
        port=int(os.environ.get("TRADINGAGENTS_DASHBOARD_PORT", "8000")),
        max_concurrent=int(os.environ.get("TRADINGAGENTS_DASHBOARD_MAX_CONCURRENT", "3")),
        price_poll_s=int(os.environ.get("TRADINGAGENTS_DASHBOARD_PRICE_POLL_S", "2")),
        log_level=os.environ.get("TRADINGAGENTS_DASHBOARD_LOG_LEVEL", "INFO"),
        frontend_dist=os.environ.get("TRADINGAGENTS_FRONTEND_DIST", "web/frontend/dist"),
    )
