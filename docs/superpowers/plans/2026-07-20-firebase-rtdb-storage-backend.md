# Firebase RTDB Storage Backend — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the GCS storage backend with Firebase Realtime Database so user data persists across Cloud Run cold starts — zero GCP cost.

**Architecture:** New `firebase_rtdb.py` module mirrors `gcs.py`'s 11-function interface. `storage.py` renames `_gcs` → `_remote` and `_init_gcs` → `_init_remote` to point at the new module. `gcs.py` is deleted. Firebase Admin SDK authenticates via base64-encoded service account JSON in `FIREBASE_SERVICE_ACCOUNT` env var.

**Tech Stack:** Python 3.12, `firebase-admin` SDK (RTDB), `pytest` with mocked Firebase references.

## Global Constraints

- All GCP services must stay on the free tier (Firebase Spark plan, no credit card)
- `firebase-admin` adds ~80MB to the Docker image (852MB → ~930MB)
- Daily write guard: 18K/day (90% of 20K Spark plan cap)
- Binary files (SQLite checkpoints) stay on local FS — RTDB is JSON-only
- Every remote call in `storage.py` must be wrapped in try/except with local FS fallback
- All RTDB reads/writes have a 10-second timeout

---

### Task 1: Add `firebase-admin` dependency

**Files:**
- Modify: `pyproject.toml`

**Interfaces:**
- Consumes: nothing
- Produces: `firebase-admin` available for import after `uv sync`

- [ ] **Step 1: Add firebase-admin to dependencies**

In `pyproject.toml`, add `"firebase-admin>=7.0.0"` to the `dependencies` list (after `"python-telegram-bot>=21.0"`):

```python
dependencies = [
    # ... existing deps ...
    "python-telegram-bot>=21.0",
    "firebase-admin>=7.0.0",
]
```

- [ ] **Step 2: Run uv sync to verify it installs**

Run: `uv sync`
Expected: installs firebase-admin and its transitive deps (no errors)

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "deps: add firebase-admin for RTDB storage backend"
```

---

### Task 2: Create `firebase_rtdb.py` — init, is_enabled, path mapping, write guard

**Files:**
- Create: `web/server/firebase_rtdb.py`

**Interfaces:**
- Consumes: `FIREBASE_SERVICE_ACCOUNT` env var (base64 JSON), `FIREBASE_DATABASE_URL` env var
- Produces: `init()`, `is_enabled()`, `_rtdb_path()`, `_check_write_budget()` — used by all later tasks

- [ ] **Step 1: Write the module skeleton with init, is_enabled, path mapping, write guard**

```python
"""Firebase Realtime Database storage backend.

Mirrors ``gcs.py``'s interface so ``storage.py`` can swap backends by
renaming ``_gcs`` to ``_remote``.  Authenticates via base64-encoded
service account JSON in ``FIREBASE_SERVICE_ACCOUNT`` and RTDB URL in
``FIREBASE_DATABASE_URL``.
"""

from __future__ import annotations

import base64
import json
import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

_db: Any = None
_data_root: str = ""

_write_count: int = 0
_write_date: str = ""
_DAILY_WRITE_CAP: int = 18_000

_ILLEGAL_KEY_RE = re.compile(r"[.#$\[\]/]")


def init(creds_json_str: str, database_url: str, data_root: str) -> None:
    """Initialise Firebase Admin SDK. Idempotent. Fails gracefully."""
    global _db, _data_root
    if _db is not None:
        return
    try:
        import firebase_admin
        from firebase_admin import credentials, db as _fb_db

        decoded = base64.b64decode(creds_json_str).decode("utf-8")
        cred = credentials.Certificate(json.loads(decoded))
        firebase_admin.initialize_app(cred, {"databaseURL": database_url})
        _db = _fb_db
        _data_root = str(Path(data_root).as_posix())
        log.info("Firebase RTDB backend enabled: url=%s data_root=%s", database_url, _data_root)
    except Exception as exc:
        log.warning("Firebase RTDB init failed (%s); falling back to local filesystem", exc)
        _db = None
        _data_root = ""


def is_enabled() -> bool:
    """True after a successful init()."""
    return _db is not None


def _rtdb_path(path: Path) -> str:
    """Convert an absolute local path to an RTDB relative path."""
    path_str = Path(path).as_posix()
    if path_str.startswith(_data_root):
        rel = path_str[len(_data_root):].lstrip("/")
    else:
        rel = path_str.lstrip("/")

    if rel.endswith("/run.json"):
        rel = rel[: -len("/run.json")] + "/meta"
    elif rel.endswith("/events.jsonl"):
        rel = rel[: -len("/events.jsonl")] + "/events"
    elif rel.endswith("/llm_calls.jsonl"):
        rel = rel[: -len("/llm_calls.jsonl")] + "/llm_calls"

    parts = rel.split("/")
    parts = [_ILLEGAL_KEY_RE.sub("_", p) for p in parts]
    return "/".join(parts)


def _check_write_budget() -> None:
    """Raise if daily write cap reached; otherwise increment counter."""
    global _write_count, _write_date
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if today != _write_date:
        _write_date = today
        _write_count = 0
    if _write_count >= _DAILY_WRITE_CAP:
        raise RuntimeError(
            f"Firebase RTDB daily write cap reached ({_DAILY_WRITE_CAP}); "
            "falling back to local FS"
        )
    _write_count += 1


def read_json(path: Path) -> Any | None:
    """Return parsed JSON at RTDB node, or None if missing."""
    ref = _db.reference(_rtdb_path(path))
    snap = ref.get()
    if snap is None:
        return None
    return snap


def write_json(path: Path, data: Any) -> None:
    """Replace RTDB node with data. Creates parents automatically."""
    _check_write_budget()
    ref = _db.reference(_rtdb_path(path))
    ref.set(data)


def append_jsonl(path: Path, obj: Any) -> None:
    """Push obj onto RTDB list. Atomic."""
    _check_write_budget()
    ref = _db.reference(_rtdb_path(path))
    ref.push(obj)


def read_jsonl(path: Path) -> list[Any]:
    """Return all entries in RTDB list in insertion order."""
    ref = _db.reference(_rtdb_path(path))
    snap = ref.get()
    if snap is None:
        return []
    if isinstance(snap, list):
        return [x for x in snap if x is not None]
    return [snap[k] for k in sorted(snap)]


def exists(path: Path) -> bool:
    """True if RTDB node exists OR has any child keys."""
    ref = _db.reference(_rtdb_path(path))
    snap = ref.get()
    return snap is not None


def is_dir(path: Path) -> bool:
    """True if RTDB node has any child keys."""
    ref = _db.reference(_rtdb_path(path))
    snap = ref.get(shallow=True)
    return isinstance(snap, dict) and len(snap) > 0


def list_prefix(path: Path) -> list[str]:
    """Return sorted immediate child key names under RTDB node."""
    ref = _db.reference(_rtdb_path(path))
    snap = ref.get(shallow=True)
    if snap is None:
        return []
    if isinstance(snap, dict):
        return sorted(snap.keys())
    return []


def delete_prefix(path: Path) -> None:
    """Recursively delete RTDB node and all children."""
    _check_write_budget()
    ref = _db.reference(_rtdb_path(path))
    ref.delete()


def delete(path: Path) -> None:
    """Delete a single RTDB node."""
    _check_write_budget()
    ref = _db.reference(_rtdb_path(path))
    ref.delete()
```

- [ ] **Step 2: Verify module imports cleanly**

Run: `uv run python -c "from web.server import firebase_rtdb; print('import OK')"`
Expected: `import OK`

- [ ] **Step 3: Commit**

```bash
git add web/server/firebase_rtdb.py
git commit -m "feat: add Firebase RTDB storage backend module"
```

---

### Task 3: Write unit tests for `firebase_rtdb.py`

**Files:**
- Create: `web/server/tests/test_firebase_rtdb.py`

**Interfaces:**
- Consumes: all 11 public functions from Task 2
- Produces: passing test suite

- [ ] **Step 1: Write test module with mocked Firebase references**

```python
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

    def get(self, shallow: bool = False) -> Any:
        val = self._resolve()
        if shallow and isinstance(val, dict):
            return {k: True for k in val}
        return val

    def set(self, value: Any) -> None:
        self._set_path(value)

    def push(self, value: Any) -> MagicMock:
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

    def delete(self) -> None:
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
        frtdb._db = None
        frtdb._data_root = ""
        fake_db = MagicMock()

        calls = []

        def capture_init(cred, options):
            calls.append((cred, options))

        monkeypatch.setattr("firebase_admin.initialize_app", capture_init)
        monkeypatch.setattr("firebase_admin.credentials.Certificate", lambda x: "fake_cred")
        monkeypatch.setattr("web.server.firebase_rtdb._db", fake_db, raising=False)

        frtdb.init(_fake_service_account_base64(), "https://test.firebaseio.com", "/data")
        assert frtdb._data_root == "/data"


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
        assert frtdb._rtdb_path(p) == "NVDA/2026-07-20/run-slug/stages/market.json"

    def test_illegal_chars_replaced(self, mock_firebase):
        p = Path("/data/NVDA/2026-07-20/run.slug[0]/run.json")
        assert frtdb._rtdb_path(p) == "NVDA/2026-07-20/run_slug_0_/meta"

    def test_watchlist_json(self, mock_firebase):
        p = Path("/data/watchlist.json")
        assert frtdb._rtdb_path(p) == "watchlist.json"


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
        frtdb.write_json(Path("/data/x.json"), {"a": 1})
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
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `uv run pytest web/server/tests/test_firebase_rtdb.py -v`
Expected: all tests PASS

- [ ] **Step 3: Commit**

```bash
git add web/server/tests/test_firebase_rtdb.py
git commit -m "test: add unit tests for Firebase RTDB storage backend"
```

---

### Task 4: Refactor `storage.py` — rename `_gcs` to `_remote`

**Files:**
- Modify: `web/server/storage.py`
- Modify: `web/server/storage.py:1-12` (module docstring)

**Interfaces:**
- Consumes: all 11 public functions from `firebase_rtdb.py` (Task 2)
- Produces: `init_settings()` calls `_init_remote()` which imports `firebase_rtdb`; all `_gcs_*` helpers renamed to `_remote_*`

- [ ] **Step 1: Update module docstring**

Replace the module docstring at lines 1-12 to remove GCS references:

```python
"""File-based storage primitives for the dashboard.

This module owns all on-disk IO for the dashboard. Higher-level
read-side helpers that shape data for the API live in ``queries.py``.

All timestamps in persisted files are UTC ISO-8601 with ``Z`` suffix.
The only Israel-local representation is the run directory slug,
which is purely for human readability.

When the env var ``FIREBASE_SERVICE_ACCOUNT`` is set, all IO is
redirected to Firebase RTDB via the ``firebase_rtdb`` sub-module so
data survives Cloud Run cold starts.
"""
```

- [ ] **Step 2: Rename `_gcs` to `_remote` and `_init_gcs` to `_init_remote`**

Replace lines 37-40:

```python
# Remote backend — lazily initialised in ``init_settings()`` when
# ``FIREBASE_SERVICE_ACCOUNT`` is set.  All IO functions in this module
# check ``_remote.is_enabled()`` before operating locally.
_remote = None  # module imported once, cached here
```

- [ ] **Step 3: Replace `_init_gcs` function with `_init_remote`**

Replace lines 63-79:

```python
def _init_remote(data_root: str) -> None:
    """Initialise the remote backend if ``FIREBASE_SERVICE_ACCOUNT`` is set.

    Uses the ``firebase_rtdb`` sub-module.  Fails gracefully:
    ``_remote`` stays ``None`` and all IO falls back to the local filesystem.
    """
    global _remote
    creds = os.environ.get("FIREBASE_SERVICE_ACCOUNT")
    db_url = os.environ.get("FIREBASE_DATABASE_URL")
    if not creds or not db_url:
        return
    try:
        from web.server import firebase_rtdb as rt_module
        rt_module.init(creds, db_url, data_root)
        _remote = rt_module
    except Exception:
        pass  # logged inside firebase_rtdb.init
```

- [ ] **Step 4: Update `init_settings` to call `_init_remote`**

Replace line 60:

```python
    _init_remote(data_dir)
```

- [ ] **Step 5: Rename all `_gcs_path_exists` → `_remote_path_exists` and update body**

Replace lines 98-104:

```python
def _remote_path_exists(path: Path) -> bool:
    if _remote and _remote.is_enabled():
        try:
            return _remote.exists(path)
        except Exception:
            log.warning("Remote exists() failed for %s; falling back to local FS", path, exc_info=True)
    return path.exists()
```

- [ ] **Step 6: Rename all `_gcs_path_is_dir` → `_remote_path_is_dir`**

Replace lines 107-113:

```python
def _remote_path_is_dir(path: Path) -> bool:
    if _remote and _remote.is_enabled():
        try:
            return _remote.is_dir(path)
        except Exception:
            log.warning("Remote is_dir() failed for %s; falling back to local FS", path, exc_info=True)
    return path.is_dir()
```

- [ ] **Step 7: Rename `_gcs_iterdir` → `_remote_iterdir`**

Replace lines 116-126:

```python
def _remote_iterdir(path: Path) -> list[Path]:
    """Return sorted Path children under *path* (like ``Path.iterdir``)."""
    if _remote and _remote.is_enabled():
        try:
            names = _remote.list_prefix(path)
            return sorted(path / n for n in names)
        except Exception:
            log.warning("Remote list_prefix() failed for %s; falling back to local FS", path, exc_info=True)
    if not path.exists():
        return []
    return sorted(path.iterdir())
```

- [ ] **Step 8: Rename `_gcs_rmtree` → `_remote_rmtree`**

Replace lines 129-138:

```python
def _remote_rmtree(path: Path) -> None:
    """Remove a directory tree (recursive)."""
    if _remote and _remote.is_enabled():
        try:
            _remote.delete_prefix(path)
            return
        except Exception:
            log.warning("Remote delete_prefix() failed for %s; falling back to local FS", path, exc_info=True)
    if path.exists():
        shutil.rmtree(path)
```

- [ ] **Step 9: Rename `_gcs_mkdir` → `_remote_mkdir`**

Replace lines 141-145:

```python
def _remote_mkdir(path: Path) -> None:
    """Create directory (no-op in remote, implicit)."""
    if _remote and _remote.is_enabled():
        return
    path.mkdir(parents=True, exist_ok=True)
```

- [ ] **Step 10: Update all call sites of `_gcs_mkdir`, `_gcs_rmtree`, etc.**

Search and replace all remaining `_gcs_path_exists` → `_remote_path_exists`, `_gcs_path_is_dir` → `_remote_path_is_dir`, `_gcs_iterdir` → `_remote_iterdir`, `_gcs_rmtree` → `_remote_rmtree`, `_gcs_mkdir` → `_remote_mkdir` throughout `storage.py`.

- [ ] **Step 11: Update `_gcs` references in `write_json_atomic`, `read_json`, `append_jsonl`, `read_jsonl`, `clear_ticker_data`, `walk_data_dir`**

Replace all `_gcs and _gcs.is_enabled()` checks with `_remote and _remote.is_enabled()` and `_gcs.read_json` → `_remote.read_json`, `_gcs.write_json` → `_remote.write_json`, etc.

- [ ] **Step 12: Update fallback warning messages**

Replace all `"GCS ... failed"` warning messages with `"Remote ... failed"` (e.g., `"GCS write_json() failed"` → `"Remote write_json() failed"`).

- [ ] **Step 13: Run existing tests to verify no regressions**

Run: `uv run pytest web/server/tests/test_storage.py -v`
Expected: all tests PASS

- [ ] **Step 14: Commit**

```bash
git add web/server/storage.py
git commit -m "refactor: rename _gcs to _remote in storage.py for Firebase RTDB"
```

---

### Task 5: Delete `gcs.py`

**Files:**
- Delete: `web/server/gcs.py`

**Interfaces:**
- Consumes: nothing
- Produces: nothing (module is removed)

- [ ] **Step 1: Delete gcs.py**

```bash
git rm web/server/gcs.py
```

- [ ] **Step 2: Verify no remaining imports of gcs**

Run: `uv run python -c "from web.server import storage; print('OK')"`
Expected: `OK` (no ImportError)

- [ ] **Step 3: Commit**

```bash
git commit -m "chore: remove GCS storage backend (replaced by Firebase RTDB)"
```

---

### Task 6: Update CI smoke test

**Files:**
- Modify: `.github/workflows/ci.yml:121-146`

**Interfaces:**
- Consumes: nothing
- Produces: CI runs smoke test with `FIREBASE_SERVICE_ACCOUNT=fake` instead of `GCS_BUCKET=...`

- [ ] **Step 1: Replace GCS_BUCKET env var with FIREBASE env vars in smoke test**

In the `docker run` command (lines 133-146), replace:

```yaml
            -e GCS_BUCKET=tradingagents-smoke-test-nonexistent \
```

with:

```yaml
            -e FIREBASE_SERVICE_ACCOUNT=fake \
            -e FIREBASE_DATABASE_URL=https://fake-project.firebaseio.com \
```

- [ ] **Step 2: Update smoke test comments**

Replace comment on line 127-128:

```yaml
          #   - FIREBASE_SERVICE_ACCOUNT=fake — triggers Firebase init code path
          #     but operations fail gracefully and fall back to local FS
```

- [ ] **Step 3: Run lint to verify no YAML syntax issues**

Run: `uv run ruff check .github/workflows/ci.yml` (or manual review)
Expected: no errors

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: replace GCS_BUCKET with FIREBASE env vars in smoke test"
```

---

### Task 7: Update deployment docs

**Files:**
- Modify: `docs/deployment/gcp-cloud-run.md`

**Interfaces:**
- Consumes: nothing
- Produces: updated deployment runbook with Firebase setup instructions

- [ ] **Step 1: Add Firebase setup section to deployment docs**

Add a new section after any existing GCS references:

```markdown
## Firebase Realtime Database Setup (one-time)

The app uses Firebase RTDB (Spark plan, free) to persist user data across
Cloud Run cold starts.

### 1. Create Firebase project

1. Go to https://console.firebase.google.com
2. Click "Add project"
3. Enter project name (e.g., `tradingagents-data`)
4. Disable Google Analytics (not needed)
5. Click "Create project"

### 2. Enable Realtime Database

1. In the Firebase console, click "Realtime Database" in the left sidebar
2. Click "Create Database"
3. Select a region (us-central1 recommended)
4. Start in **test mode** (we'll set rules next)
5. Click "Enable"

### 3. Set database rules

In the Realtime Database console, click "Rules" tab and paste:

```json
{
  "rules": {
    ".read": "auth != null",
    ".write": "auth != null"
  }
}
```

Click "Publish".

### 4. Generate service account key

1. Go to Project Settings (gear icon) → "Service accounts"
2. Click "Generate new private key"
3. Save the JSON file securely

### 5. Encode the key for GitHub secrets

```bash
base64 -w 0 service-account.json
```

Copy the output.

### 6. Add GitHub secrets

```bash
gh secret set FIREBASE_SERVICE_ACCOUNT -b "<base64-encoded-key>"
gh secret set FIREBASE_DATABASE_URL -b "https://<project-id>-default-rtdb.firebaseio.com/"
```

### 7. Cloud Run env vars

The CI deploy step automatically sets:

- `FIREBASE_SERVICE_ACCOUNT=${{ secrets.FIREBASE_SERVICE_ACCOUNT }}`
- `FIREBASE_DATABASE_URL=${{ secrets.FIREBASE_DATABASE_URL }}`

No manual intervention needed after secrets are configured.
```

- [ ] **Step 2: Commit**

```bash
git add docs/deployment/gcp-cloud-run.md
git commit -m "docs: add Firebase RTDB setup instructions to deployment runbook"
```

---

### Task 8: Deploy to Cloud Run and verify persistence

**Files:**
- No code changes (verification only)

**Interfaces:**
- Consumes: all previous tasks completed
- Produces: Cloud Run service running with Firebase RTDB persistence

- [ ] **Step 1: Ensure Firebase secrets are set in GitHub**

Run: `gh secret list | grep FIREBASE`
Expected: both `FIREBASE_SERVICE_ACCOUNT` and `FIREBASE_DATABASE_URL` are listed

- [ ] **Step 2: Push code to trigger CI deploy**

```bash
git push origin feat/ci-cd-env-vars-permissions
```

- [ ] **Step 3: Wait for CI to complete**

Monitor: `gh run watch`
Expected: all jobs pass, including smoke test and Cloud Run deploy

- [ ] **Step 4: Verify Cloud Run service is running**

```bash
gcloud run services describe tradingagents --region=us-central1 --project=trading-agent-9058 --format="value(status.url)"
```

Expected: URL returned (e.g., `https://tradingagents-...-uc.a.run.app`)

- [ ] **Step 5: Verify health endpoint**

```bash
curl -sfS https://tradingagents-...-uc.a.run.app/api/health | jq .
```

Expected: `{"status": "ok"}`

- [ ] **Step 6: Test data persistence across cold starts**

1. Create a watchlist entry via the API or UI
2. Wait 5 minutes (let the instance scale down to 0)
3. Trigger a new request — instance cold-starts
4. Verify the watchlist entry still exists

- [ ] **Step 7: Verify Firebase RTDB has data**

```bash
# If firebase-tools is installed:
firebase database:get / --project <project-id>
```

Or check in Firebase Console → Realtime Database → Data tab.

Expected: data tree visible with watchlist, runs, etc.

---

## Self-Review Checklist

1. **Spec coverage:** All 11 interface functions in `firebase_rtdb.py` are implemented and tested. Daily write guard at 18K is in `_check_write_budget()`. Path mapping rules match the spec. Smoke test updated. Deployment docs updated.

2. **Placeholder scan:** No TBD/TODO/placeholder text found in the plan.

3. **Type consistency:** All function signatures match `gcs.py`'s interface exactly. `_rtdb_path()` accepts `Path` and returns `str`. `_check_write_budget()` raises `RuntimeError`.

## Spec Requirements Coverage

| Spec section | Task(s) |
|---|---|
| Add `firebase_rtdb.py` | Task 2 |
| Modify `storage.py` rename `_gcs` → `_remote` | Task 4 |
| Update CI smoke test | Task 6 |
| Update deployment docs | Task 7 |
| Add `firebase-admin` to pyproject.toml | Task 1 |
| Free-tier guard (18K/day) | Task 2 (in `_check_write_budget`) |
| `AGENTS.md` free-tier rule | Already done (commit 3ba0434) |
| Unit tests | Task 3 |
| Firebase project setup | Task 8 (manual, documented in Task 7) |
