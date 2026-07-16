from __future__ import annotations

import os


def get_database_url() -> str | None:
    """Return the async database URL from env, or None if not configured.

    Supports two modes:
    1. CLOUD_SQL_CONNECTION_NAME set → build connector URL
    2. DATABASE_URL set → use as-is (raw connection string)
    """
    url = os.environ.get("DATABASE_URL")
    if url:
        return url
    connection_name = os.environ.get("CLOUD_SQL_CONNECTION_NAME")
    if connection_name:
        db_name = os.environ.get("DB_NAME", "tradingagents")
        db_user = os.environ.get("DB_USER", "app")
        db_password = os.environ.get("DB_PASSWORD", "")
        return f"postgresql+asyncpg://{db_user}:{db_password}@{connection_name}/{db_name}"
    return None


def get_sync_database_url() -> str | None:
    """Return the sync database URL (for Alembic)."""
    url = os.environ.get("DATABASE_URL_SYNC")
    if url:
        return url
    async_url = get_database_url()
    if async_url:
        return async_url.replace("+asyncpg", "+psycopg2")
    return None


def get_upstash_config() -> dict:
    """Return Upstash Redis config from env vars."""
    return {
        "url": os.environ.get("UPSTASH_REDIS_URL", ""),
        "token": os.environ.get("UPSTASH_REDIS_TOKEN", ""),
    }
