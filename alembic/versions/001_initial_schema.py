"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-07-16 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "watchlist",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("ticker", sa.String(20), nullable=False, unique=True, index=True),
        sa.Column("company_name", sa.String(200), server_default=""),
        sa.Column("exchange", sa.String(50), server_default=""),
        sa.Column("source", sa.String(50), server_default="user"),
        sa.Column("sort_order", sa.Integer(), server_default="0"),
        sa.Column("group_name", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "runs",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("ticker", sa.String(20), nullable=False, index=True),
        sa.Column("date", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), server_default="queued"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("cancel_requested", sa.Integer(), server_default="0"),
        sa.Column("run_type", sa.String(20), server_default="manual"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "run_events",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("run_id", sa.String(36), nullable=False, index=True),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("data", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "llm_calls",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("run_id", sa.String(36), nullable=False, index=True),
        sa.Column("provider", sa.String(50), nullable=True),
        sa.Column("model", sa.String(100), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("duration_ms", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "indicators",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("kind", sa.String(50), nullable=False),
        sa.Column("name", sa.String(100), nullable=True),
        sa.Column("threshold", sa.Float(), nullable=True),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("enabled", sa.Integer(), server_default="1"),
        sa.Column("ticker", sa.String(20), nullable=True),
        sa.Column("comparator", sa.String(10), nullable=True),
        sa.Column("triggered", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "indicator_schedule",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("interval_ms", sa.Integer(), server_default="0"),
        sa.Column("last_check_at", sa.String(30), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "app_config",
        sa.Column("key", sa.String(100), nullable=False),
        sa.Column("value", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("key"),
    )
    op.create_table(
        "notifier_config",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("enabled", sa.Integer(), server_default="0"),
        sa.Column("bot_token", sa.String(200), nullable=True),
        sa.Column("chat_id", sa.String(50), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "background_jobs",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("ticker", sa.String(20), nullable=False),
        sa.Column("date_from", sa.String(20), nullable=False),
        sa.Column("date_to", sa.String(20), nullable=False),
        sa.Column("every", sa.String(10), server_default="1d"),
        sa.Column("parallel", sa.Integer(), server_default="1"),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("background_jobs")
    op.drop_table("notifier_config")
    op.drop_table("app_config")
    op.drop_table("indicator_schedule")
    op.drop_table("indicators")
    op.drop_table("llm_calls")
    op.drop_table("run_events")
    op.drop_table("runs")
    op.drop_table("watchlist")
