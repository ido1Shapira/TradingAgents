# Task 2: Create `firebase_rtdb.py` — init, is_enabled, path mapping, write guard

**Files:**
- Create: `web/server/firebase_rtdb.py`

**Interfaces:**
- Consumes: `FIREBASE_SERVICE_ACCOUNT` env var (base64 JSON), `FIREBASE_DATABASE_URL` env var
- Produces: `init()`, `is_enabled()`, `_rtdb_path()`, `_check_write_budget()` — used by all later tasks

## Steps

- [ ] **Step 1: Write the module with all 11 functions + write guard**

Create `web/server/firebase_rtdb.py` with:

1. Module-level globals: `_db`, `_data_root`, `_write_count`, `_write_date`, `_DAILY_WRITE_CAP` (18000), `_ILLEGAL_KEY_RE`
2. `init(creds_json_str, database_url, data_root)` — decode base64 creds, initialize Firebase Admin SDK, idempotent, fails gracefully
3. `is_enabled()` — returns `_db is not None`
4. `_rtdb_path(path)` — converts absolute local path to RTDB relative path:
   - Strips `_data_root` prefix
   - `run.json` → `meta`
   - `events.jsonl` → `events`
   - `llm_calls.jsonl` → `llm_calls`
   - Replaces illegal RTDB key chars (`.#$/[]`) with `_`
5. `_check_write_budget()` — raises `RuntimeError` if daily cap reached, otherwise increments counter; resets at UTC midnight
6. `read_json(path)` — `ref.get()`, returns None if missing
7. `write_json(path, data)` — `_check_write_budget()` then `ref.set(data)`
8. `append_jsonl(path, obj)` — `_check_write_budget()` then `ref.push(obj)`
9. `read_jsonl(path)` — `ref.get()`, handles list vs dict (push keys), returns sorted entries
10. `exists(path)` — `ref.get() is not None`
11. `is_dir(path)` — `ref.get(shallow=True)` is dict with keys
12. `list_prefix(path)` — `ref.get(shallow=True)`, returns sorted keys
13. `delete_prefix(path)` — `_check_write_budget()` then `ref.delete()`
14. `delete(path)` — `_check_write_budget()` then `ref.delete()`

Full code:

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
