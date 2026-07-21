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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

_db: Any = None
_data_root: str = ""

_write_count: int = 0
_write_date: str = ""
_DAILY_WRITE_CAP: int = 18_000

_ILLEGAL_KEY_RE = re.compile(r"[#$\[\]/]")


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
    if ".." in Path(path).parts:
        raise ValueError(
            f"Path {path} contains '..'; "
            "RTDB paths must not escape the data directory"
        )
    path_str = Path(path).as_posix()
    root = Path(_data_root).as_posix() if _data_root else ""
    if path_str.startswith(root):
        rel = path_str[len(root):].lstrip("/")
    else:
        raise ValueError(
            f"Path {path} is outside data_root {_data_root}; "
            "RTDB paths must be under the data directory"
        )

    # File-name remapping for known patterns
    if rel.endswith("/run.json"):
        rel = rel[: -len("/run.json")] + "/meta"
    elif rel.endswith("/events.jsonl"):
        rel = rel[: -len("/events.jsonl")] + "/events"
    elif rel.endswith("/llm_calls.jsonl"):
        rel = rel[: -len("/llm_calls.jsonl")] + "/llm_calls"
    else:
        # Top-level singleton rewrites
        if rel == "watchlist.json":
            rel = "_watchlist"
        elif rel == "indicators.json":
            rel = "_indicators"
        elif rel == "notifier.json":
            rel = "_notifier"
        elif rel == "indicator_state.json":
            rel = "_indicator_state"
        elif rel == "indicator_schedule.json":
            rel = "_indicator_schedule"
        elif rel.endswith(".json"):
            # Strip .json suffix for any other JSON files (e.g. stages/market.json → stages/market)
            rel = rel[: -len(".json")]
        elif rel.endswith(".jsonl"):
            # Strip .jsonl suffix for any other JSONL files
            rel = rel[: -len(".jsonl")]

    parts = rel.split("/")
    parts = [_ILLEGAL_KEY_RE.sub("_", p) for p in parts]
    return "/".join(parts)


def _check_write_budget_pre() -> None:
    """Raise if daily write cap reached. Does NOT increment."""
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


def _increment_write_count() -> None:
    """Increment the daily write counter after a successful operation."""
    global _write_count
    _write_count += 1


def read_json(path: Path) -> Any | None:
    """Return parsed JSON at RTDB node, or None if missing."""
    ref = _db.reference(_rtdb_path(path))
    snap = ref.get(timeout=10)
    if snap is None:
        return None
    return snap


def write_json(path: Path, data: Any) -> None:
    """Replace RTDB node with data. Creates parents automatically."""
    _check_write_budget_pre()
    ref = _db.reference(_rtdb_path(path))
    ref.set(data, timeout=10)
    _increment_write_count()


def append_jsonl(path: Path, obj: Any) -> None:
    """Push obj onto RTDB list. Atomic."""
    _check_write_budget_pre()
    ref = _db.reference(_rtdb_path(path))
    ref.push(obj, timeout=10)
    _increment_write_count()


def read_jsonl(path: Path) -> list[Any]:
    """Return all entries in RTDB list in insertion order."""
    ref = _db.reference(_rtdb_path(path))
    snap = ref.get(timeout=10)
    if snap is None:
        return []
    if isinstance(snap, list):
        return [x for x in snap if x is not None]
    return [snap[k] for k in sorted(snap)]


def exists(path: Path) -> bool:
    """True if RTDB node exists OR has any child keys."""
    ref = _db.reference(_rtdb_path(path))
    snap = ref.get(timeout=10)
    return snap is not None


def is_dir(path: Path) -> bool:
    """True if RTDB node has any child keys."""
    ref = _db.reference(_rtdb_path(path))
    snap = ref.get(shallow=True, timeout=10)
    return isinstance(snap, dict) and len(snap) > 0


def list_prefix(path: Path) -> list[str]:
    """Return sorted immediate child key names under RTDB node."""
    ref = _db.reference(_rtdb_path(path))
    snap = ref.get(shallow=True, timeout=10)
    if snap is None:
        return []
    if isinstance(snap, dict):
        return sorted(snap.keys())
    return []


def delete_prefix(path: Path) -> None:
    """Recursively delete RTDB node and all children."""
    _check_write_budget_pre()
    ref = _db.reference(_rtdb_path(path))
    ref.delete(timeout=10)
    _increment_write_count()


def delete(path: Path) -> None:
    """Delete a single RTDB node."""
    _check_write_budget_pre()
    ref = _db.reference(_rtdb_path(path))
    ref.delete(timeout=10)
    _increment_write_count()
