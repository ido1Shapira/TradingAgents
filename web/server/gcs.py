"""GCS storage backend for the dashboard.

Replaces local filesystem operations with GCS blob reads/writes when
``GCS_BUCKET`` is set.  Designed to be called from ``storage.py``.

Local filesystem semantics preserved:
  - ``data_dir/TICKER/slug/run.json`` → GCS key ``data/TICKER/slug/run.json``
  - ``data_dir/TICKER/slug/stages/stage.json`` → GCS key ``data/TICKER/slug/stages/stage.json``
  - ``data_dir/watchlist.json`` → GCS key ``data/watchlist.json``
"""

from __future__ import annotations

import json
import logging
from pathlib import Path, PurePosixPath
from typing import Any

log = logging.getLogger(__name__)

_client = None
_bucket = None
_data_root: str = ""


def init(bucket_name: str, data_root: str) -> None:
    """Initialize the GCS client and set the local data-root prefix."""
    global _client, _bucket, _data_root
    try:
        from google.cloud import storage as gcs
        _client = gcs.Client()
        _bucket = _client.bucket(bucket_name)
    except Exception as exc:
        log.warning("GCS init failed (%s); falling back to local filesystem", exc)
        _client = None
        _bucket = None
        return
    _data_root = str(PurePosixPath(data_root))
    log.info("GCS backend enabled: bucket=%s data_root=%s", bucket_name, _data_root)


def is_enabled() -> bool:
    return _bucket is not None


def _bucket_ensure():
    b = _bucket
    if b is None:
        raise RuntimeError("GCS not initialized")
    return b


def _key(path: Path) -> str:
    """Return the GCS object key for an absolute local *path*."""
    path_str = str(PurePosixPath(path))
    if path_str.startswith(_data_root):
        rel = path_str[len(_data_root):].lstrip("/")
        return rel
    return path_str.lstrip("/")


def read_json(path: Path) -> Any | None:
    b = _bucket_ensure()
    blob = b.blob(_key(path))
    if not blob.exists():
        return None
    try:
        raw = blob.download_as_bytes()
        return json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as exc:
        log.warning("GCS read_json: %s is malformed (%s); returning None", path, exc)
        return None


def write_json(path: Path, data: Any) -> None:
    b = _bucket_ensure()
    blob = b.blob(_key(path))
    blob.upload_from_string(
        json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False),
        content_type="application/json",
    )


def append_jsonl(path: Path, obj: Any) -> None:
    b = _bucket_ensure()
    key = _key(path)
    blob = b.blob(key)
    line = json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n"
    if blob.exists():
        existing = blob.download_as_bytes().decode("utf-8")
        blob.upload_from_string(existing + line, content_type="application/x-ndjson")
    else:
        blob.upload_from_string(line, content_type="application/x-ndjson")


def read_jsonl(path: Path) -> list[Any]:
    b = _bucket_ensure()
    blob = b.blob(_key(path))
    if not blob.exists():
        return []
    raw = blob.download_as_bytes().decode("utf-8")
    out: list[Any] = []
    for line in raw.splitlines():
        s = line.strip()
        if not s:
            continue
        try:
            out.append(json.loads(s))
        except json.JSONDecodeError:
            continue
    return out


def exists(path: Path) -> bool:
    """Check if a blob or directory prefix exists in GCS."""
    b = _bucket_ensure()
    key = _key(path)
    if not key:
        return _prefix_has_children(b, key)
    blob = b.blob(key)
    if blob.exists():
        return True
    return _prefix_has_children(b, key)


def is_dir(path: Path) -> bool:
    """Check if a path has children in GCS (like a directory)."""
    b = _bucket_ensure()
    key = _key(path)
    return _prefix_has_children(b, key)


def _prefix_has_children(bucket, key: str) -> bool:
    """Check if any blob exists under the given key prefix."""
    prefix = key if not key or key.endswith("/") else key + "/"
    for _ in bucket.list_blobs(max_results=1, prefix=prefix):
        return True
    return False


def list_prefix(path: Path) -> list[str]:
    """List immediate children (blobs and sub-prefixes) under *path*.

    Returns basenames only — e.g. ``["NVDA", "QQQ", "watchlist.json"]``.
    Uses GCS ``delimiter="/"`` for efficient directory simulation.
    """
    b = _bucket_ensure()
    prefix = _key(path)
    if prefix and not prefix.endswith("/"):
        prefix += "/"
    seen: set[str] = set()
    plen = len(prefix)
    iterator = b.list_blobs(prefix=prefix, delimiter="/")
    for page in iterator.pages:
        for p in page.prefixes:
            rest = p[plen:].rstrip("/")
            if rest:
                seen.add(rest)
    for blob in iterator:
        name = blob.name
        if name.startswith(prefix):
            rest = name[plen:]
            if rest and "/" not in rest:
                seen.add(rest)
    return sorted(seen)


def delete_prefix(path: Path) -> None:
    """Delete all blobs under the given key prefix (recursive)."""
    b = _bucket_ensure()
    prefix = _key(path)
    if prefix and not prefix.endswith("/"):
        prefix += "/"
    blobs = list(b.list_blobs(prefix=prefix))
    if blobs:
        b.delete_blobs(blobs)


def delete(path: Path) -> None:
    """Delete a single blob."""
    b = _bucket_ensure()
    key = _key(path)
    if not key:
        return
    blob = b.blob(key)
    if blob.exists():
        blob.delete()
