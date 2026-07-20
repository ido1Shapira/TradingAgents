"""Unit tests for ``web.server.firebase_rtdb`` with mocked Firebase Admin SDK."""
from __future__ import annotations

import base64
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from web.server import firebase_rtdb as frtdb


# ── helpers ─────────────────────────────────────────────────────────────


def _fake_service_account_base64() -> str:
    """Return a base64-encoded fake service account JSON."""
    sa = {
        "type": "service_account",
        "project_id": "test-project",
        "private_key_id": "abc123",
        "private_key": "-----BEGIN RSA PRIVATE KEY-----\nfake\n-----END RSA PRIVATE KEY-----\n",
        "client_email": "test@test-project.iam.gserviceaccount.com",
        "client_id": "123456789",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
    return base64.b64encode(json.dumps(sa).encode()).decode()


class FakeRef:
    """In-memory fake for a Firebase RTDB reference node."""

    def __init__(self, tree: dict, path: str):
        self._tree = tree
        self._path = path

    def _resolve(self) -> Any:
        parts = [p for p in self._path.split("/") if p]
        node = self._tree
        for p in parts:
            if isinstance(node, dict) and p in node:
                node = node[p]
            else:
                return None
        return node

    def _set_path(self, value: Any) -> None:
        parts = [p for p in self._path.split("/") if p]
        node = self._tree
        for p in parts[:-1]:
            if p not in node:
                node[p] = {}
            node = node[p]
        node[parts[-1]] = value

    def _delete_path(self) -> None:
        parts = [p for p in self._path.split("/") if p]
        node = self._tree
        for p in parts[:-1]:
            if p not in node:
                return
            node = node[p]
        node.pop(parts[-1], None)

    def get(self, shallow: bool = False, timeout: int | None = None) -> Any:
        val = self._resolve()
        if shallow and isinstance(val, dict):
            return {k: True for k in val}
        return val

    def set(self, value: Any, timeout: int | None = None) -> None:
        self._set_path(value)

    def push(self, value: Any, timeout: int | None = None) -> MagicMock:
        node = self._resolve()
        if not isinstance(node, dict):
            parent_parts = [p for p in self._path.split("/") if p]
            grandparent = self._tree
            for p in parent_parts[:-1]:
                if p not in grandparent:
                    grandparent[p] = {}
                grandparent = grandparent[p]
            grandparent[parent_parts[-1]] = {}
            node = grandparent[parent_parts[-1]]
        key = f"push_{len(node)}"
        node[key] = value
        return MagicMock(key=key)

    def delete(self, timeout: int | None = None) -> None:
        self._delete_path()


@pytest.fixture
def fake_tree():
    """Shared in-memory tree for all tests."""
    tree: dict = {}
    yield tree


@pytest.fixture
def mock_firebase(fake_tree, monkeypatch):
    """Initialise frtdb with a mocked Firebase reference tree."""
    frtdb._db = None
    frtdb._data_root = ""
    frtdb._write_count = 0
    frtdb._write_date = ""

    mock_db_module = MagicMock()

    def fake_reference(path: str) -> FakeRef:
        return FakeRef(fake_tree, path)

    mock_db_module.reference = fake_reference
    monkeypatch.setattr("web.server.firebase_rtdb._db", mock_db_module, raising=False)
    frtdb._data_root = "/data"
    yield fake_tree


@pytest.fixture(autouse=True)
def _reset_globals():
    """Reset module globals between tests."""
    yield
    frtdb._db = None
    frtdb._data_root = ""
    frtdb._write_count = 0
    frtdb._write_date = ""


# ── init / is_enabled ──────────────────────────────────────────────────


class TestInit:
    def test_is_enabled_after_successful_init(self, monkeypatch):
        frtdb._db = None
        fake_db = MagicMock()
        monkeypatch.setattr("web.server.firebase_rtdb._db", fake_db, raising=False)
        frtdb._data_root = "/data"
        assert frtdb.is_enabled() is True

    def test_is_disabled_when_db_is_none(self):
        frtdb._db = None
        assert frtdb.is_enabled() is False

    def test_init_sets_db_and_data_root(self, monkeypatch):
        import sys

        frtdb._db = None
        frtdb._data_root = ""

        fake_firebase_admin = MagicMock()
        monkeypatch.setitem(sys.modules, "firebase_admin", fake_firebase_admin)
        monkeypatch.setitem(sys.modules, "firebase_admin.credentials", fake_firebase_admin.credentials)
        monkeypatch.setitem(sys.modules, "firebase_admin.db", fake_firebase_admin.db)

        frtdb.init(_fake_service_account_base64(), "https://test.firebaseio.com", "/data")
        assert frtdb._data_root == "/data"
        assert frtdb._db is fake_firebase_admin.db


# ── _rtdb_path ─────────────────────────────────────────────────────────


class TestRtdbPath:
    def test_run_json_maps_to_meta(self, mock_firebase):
        p = Path("/data/NVDA/2026-07-20/run-slug/run.json")
        assert frtdb._rtdb_path(p) == "NVDA/2026-07-20/run-slug/meta"

    def test_events_jsonl_maps_to_events(self, mock_firebase):
        p = Path("/data/NVDA/2026-07-20/run-slug/events.jsonl")
        assert frtdb._rtdb_path(p) == "NVDA/2026-07-20/run-slug/events"

    def test_llm_calls_jsonl_maps_to_llm_calls(self, mock_firebase):
        p = Path("/data/NVDA/2026-07-20/run-slug/llm_calls.jsonl")
        assert frtdb._rtdb_path(p) == "NVDA/2026-07-20/run-slug/llm_calls"

    def test_stage_json_maps_directly(self, mock_firebase):
        p = Path("/data/NVDA/2026-07-20/run-slug/stages/market.json")
        assert frtdb._rtdb_path(p) == "NVDA/2026-07-20/run-slug/stages/market_json"

    def test_illegal_chars_replaced(self, mock_firebase):
        p = Path("/data/NVDA/2026-07-20/run.slug[0]/run.json")
        assert frtdb._rtdb_path(p) == "NVDA/2026-07-20/run_slug_0_/meta"

    def test_watchlist_json(self, mock_firebase):
        p = Path("/data/watchlist.json")
        assert frtdb._rtdb_path(p) == "watchlist_json"


# ── write_json / read_json ─────────────────────────────────────────────


class TestWriteReadJson:
    def test_write_then_read(self, mock_firebase):
        p = Path("/data/watchlist.json")
        frtdb.write_json(p, {"tickers": ["NVDA"]})
        assert frtdb.read_json(p) == {"tickers": ["NVDA"]}

    def test_read_returns_none_for_missing(self, mock_firebase):
        assert frtdb.read_json(Path("/data/absent.json")) is None

    def test_overwrite(self, mock_firebase):
        p = Path("/data/x.json")
        frtdb.write_json(p, {"v": 1})
        frtdb.write_json(p, {"v": 2})
        assert frtdb.read_json(p) == {"v": 2}


# ── append_jsonl / read_jsonl ──────────────────────────────────────────


class TestAppendReadJsonl:
    def test_append_then_read(self, mock_firebase):
        p = Path("/data/NVDA/2026-07-20/run-slug/events.jsonl")
        frtdb.append_jsonl(p, {"e": "start"})
        frtdb.append_jsonl(p, {"e": "end"})
        result = frtdb.read_jsonl(p)
        assert len(result) == 2
        assert result[0]["e"] == "start"
        assert result[1]["e"] == "end"

    def test_read_jsonl_empty_when_missing(self, mock_firebase):
        assert frtdb.read_jsonl(Path("/data/absent.jsonl")) == []


# ── exists / is_dir ────────────────────────────────────────────────────


class TestExistsIsDir:
    def test_exists_true_when_node_present(self, mock_firebase):
        frtdb.write_json(Path("/data/x.json"), {"a": 1})
        assert frtdb.exists(Path("/data/x.json")) is True

    def test_exists_false_when_missing(self, mock_firebase):
        assert frtdb.exists(Path("/data/absent.json")) is False

    def test_is_dir_true_for_dict_node(self, mock_firebase):
        frtdb.write_json(Path("/data/tickers/NVDA/meta.json"), {"t": "NVDA"})
        assert frtdb.is_dir(Path("/data/tickers")) is True

    def test_is_dir_false_for_leaf(self, mock_firebase):
        frtdb.write_json(Path("/data/x.json"), "leaf_value")
        assert frtdb.is_dir(Path("/data/x.json")) is False


# ── list_prefix ────────────────────────────────────────────────────────


class TestListPrefix:
    def test_list_returns_sorted_children(self, mock_firebase):
        frtdb.write_json(Path("/data/tickers/AAPL/meta.json"), {})
        frtdb.write_json(Path("/data/tickers/NVDA/meta.json"), {})
        frtdb.write_json(Path("/data/tickers/MSFT/meta.json"), {})
        result = frtdb.list_prefix(Path("/data/tickers"))
        assert result == ["AAPL", "MSFT", "NVDA"]

    def test_list_empty_when_missing(self, mock_firebase):
        assert frtdb.list_prefix(Path("/data/absent")) == []


# ── delete / delete_prefix ─────────────────────────────────────────────


class TestDelete:
    def test_delete_single(self, mock_firebase):
        frtdb.write_json(Path("/data/x.json"), {"a": 1})
        frtdb.delete(Path("/data/x.json"))
        assert frtdb.exists(Path("/data/x.json")) is False

    def test_delete_prefix_removes_all_children(self, mock_firebase):
        frtdb.write_json(Path("/data/tickers/NVDA/meta.json"), {})
        frtdb.write_json(Path("/data/tickers/AAPL/meta.json"), {})
        frtdb.delete_prefix(Path("/data/tickers"))
        assert frtdb.exists(Path("/data/tickers")) is False


# ── write guard ────────────────────────────────────────────────────────


class TestWriteGuard:
    def test_raises_when_cap_reached(self, mock_firebase):
        frtdb._write_count = frtdb._DAILY_WRITE_CAP
        frtdb._write_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        with pytest.raises(RuntimeError, match="daily write cap"):
            frtdb.write_json(Path("/data/x.json"), {"a": 1})

    def test_counter_resets_on_new_day(self, mock_firebase):
        frtdb._write_count = frtdb._DAILY_WRITE_CAP
        frtdb._write_date = "2000-01-01"  # old date
        frtdb.write_json(Path("/data/x.json"), {"a": 1})
        assert frtdb._write_count == 1

    def test_counter_increments(self, mock_firebase):
        frtdb._write_count = 0
        frtdb._write_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        frtdb.write_json(Path("/data/x.json"), {"a": 1})
        frtdb.write_json(Path("/data/x.json"), {"a": 2})
        assert frtdb._write_count == 2
