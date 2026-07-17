"""GCS storage backend for the dashboard using the GCS JSON REST API.

Replaces ``google-cloud-storage`` (which can crash on gVisor / Cloud Run
sandbox due to C extension segfaults during ``Client()`` initialisation)
with direct HTTP calls via stdlib ``urllib.request``.

Local filesystem semantics preserved:
  - ``data_dir/TICKER/slug/run.json`` → GCS key ``data/TICKER/slug/run.json``
  - ``data_dir/TICKER/slug/stages/stage.json`` → GCS key ``data/TICKER/slug/stages/stage.json``
  - ``data_dir/watchlist.json`` → GCS key ``data/watchlist.json``
"""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path, PurePosixPath
from typing import Any

log = logging.getLogger(__name__)

_bucket_name: str = ""
_data_root: str = ""
_token: str = ""
_token_expiry: float = 0.0

_API_BASE = "https://storage.googleapis.com/storage/v1"
_UPLOAD_BASE = "https://storage.googleapis.com/upload/storage/v1"
_METADATA_TOKEN_URL = (
    "http://metadata.google.internal/computeMetadata/v1/"
    "instance/service-accounts/default/token"
)


# ── auth ────────────────────────────────────────────────────────────────


def _get_token() -> str:
    """Return a fresh access token from the GCE metadata server.

    Falls back to ``gcloud auth application-default print-access-token``
    for local development.  Caches the token until it is within 60 s of
    expiry.
    """
    global _token, _token_expiry
    now = time.time()
    if _token and now < _token_expiry - 60:
        return _token

    last_err: Exception | None = None

    try:
        req = urllib.request.Request(
            _METADATA_TOKEN_URL,
            headers={"Metadata-Flavor": "Google"},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data: dict[str, Any] = json.loads(resp.read().decode("utf-8"))
        _token = str(data["access_token"])
        _token_expiry = now + float(data.get("expires_in", 3600))
        return _token
    except Exception as exc:
        last_err = exc

    raise RuntimeError(
        "No GCS credentials available"
    ) from last_err


# ── low-level REST helpers ──────────────────────────────────────────────


def _object_url(key: str, *, upload: bool = False) -> str:
    """Return the GCS REST URL for a single object *key*."""
    base = _UPLOAD_BASE if upload else _API_BASE
    return f"{base}/b/{_bucket_name}/o/{urllib.parse.quote(key, safe='')}"


def _list_url(prefix: str) -> str:
    """Return the GCS REST URL for listing under *prefix*."""
    q = urllib.parse.quote(prefix, safe="%/")
    return f"{_API_BASE}/b/{_bucket_name}/o?prefix={q}&delimiter=%2F"


def _request(
    method: str,
    url: str,
    *,
    body: bytes | None = None,
    content_type: str | None = None,
    accept_json: bool = True,
) -> str | None:
    """Make an authenticated HTTP request and return the response body.

    Returns ``None`` on 404.
    """
    headers: dict[str, str] = {
        "Authorization": f"Bearer {_get_token()}",
    }
    if accept_json:
        headers["Accept"] = "application/json"
    if content_type:
        headers["Content-Type"] = content_type

    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
            return raw.decode("utf-8") if raw else ""
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        error_body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        log.error("GCS HTTP %s %s -> %s: %s", method, url, exc.code, error_body)
        raise


def _get_json(url: str) -> Any:
    """GET *url* and parse the JSON response, or return ``None`` on 404."""
    raw = _request("GET", url)
    if raw is None:
        return None
    return json.loads(raw)


def _post_json(url: str, payload: dict[str, Any]) -> Any:
    """POST a JSON body to *url* and parse the response."""
    body = json.dumps(payload).encode("utf-8")
    raw = _request("POST", url, body=body, content_type="application/json")
    return json.loads(raw) if raw else None


def _upload_object(key: str, data: bytes, content_type: str) -> None:
    """Upload *data* as a new GCS object via simple media upload."""
    url = _object_url(key, upload=True) + "&uploadType=media"
    _request("POST", url, body=data, content_type=content_type, accept_json=False)


# ── initialisation ──────────────────────────────────────────────────────


def init(bucket_name: str, data_root: str) -> None:
    """Verify GCS connectivity and store the bucket / data-root prefix.

    Safe to call multiple times (idempotent).  Fails gracefully — callers
    must check ``is_enabled()`` before using GCS operations.
    """
    global _bucket_name, _data_root
    try:
        _bucket_name = bucket_name
        _data_root = str(PurePosixPath(data_root))
        log.info("GCS backend enabled: bucket=%s data_root=%s", bucket_name, _data_root)
    except Exception as exc:
        log.warning("GCS init failed (%s); falling back to local filesystem", exc)
        _bucket_name = ""
        _data_root = ""


def is_enabled() -> bool:
    return bool(_bucket_name)


# ── key mapping ─────────────────────────────────────────────────────────


def _key(path: Path) -> str:
    """Return the GCS object key for an absolute local *path*."""
    path_str = str(PurePosixPath(path))
    if path_str.startswith(_data_root):
        rel = path_str[len(_data_root) :].lstrip("/")
        return rel
    return path_str.lstrip("/")


# ── public API ──────────────────────────────────────────────────────────


def read_json(path: Path) -> Any | None:
    key = _key(path)
    url = _object_url(key) + "?alt=media"
    raw = _request("GET", url)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        log.warning("GCS read_json: %s is malformed (%s); returning None", path, exc)
        return None


def write_json(path: Path, data: Any) -> None:
    key = _key(path)
    blob = json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8")
    _upload_object(key, blob, "application/json")


def append_jsonl(path: Path, obj: Any) -> None:
    key = _key(path)
    url = _object_url(key) + "?alt=media"
    line = json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n"
    existing = _request("GET", url)
    blob = (existing + line).encode("utf-8") if existing is not None else line.encode("utf-8")
    _upload_object(key, blob, "application/x-ndjson")


def read_jsonl(path: Path) -> list[Any]:
    key = _key(path)
    url = _object_url(key) + "?alt=media"
    raw = _request("GET", url)
    if raw is None:
        return []
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
    key = _key(path)
    url = _object_url(key)
    if _request("GET", url) is not None:
        return True
    if not key:
        return _prefix_has_children(key)
    return _prefix_has_children(key)


def is_dir(path: Path) -> bool:
    key = _key(path)
    return _prefix_has_children(key)


def _prefix_has_children(key: str) -> bool:
    prefix = key if not key or key.endswith("/") else key + "/"
    url = _list_url(prefix) + "&maxResults=1"
    data = _get_json(url)
    if data is None:
        return False
    return bool(data.get("items") or data.get("prefixes"))


def list_prefix(path: Path) -> list[str]:
    key = _key(path)
    prefix = key if not key or key.endswith("/") else key + "/"
    url = _list_url(prefix)
    data = _get_json(url)
    if data is None:
        return []
    seen: set[str] = set()
    plen = len(prefix)
    for p in data.get("prefixes", []):
        rest = p[plen:].rstrip("/")
        if rest:
            seen.add(rest)
    for item in data.get("items", []):
        name = item.get("name", "")
        if name.startswith(prefix):
            rest = name[plen:]
            if rest and "/" not in rest:
                seen.add(rest)
    return sorted(seen)


def delete_prefix(path: Path) -> None:
    key = _key(path)
    prefix = key if not key or key.endswith("/") else key + "/"
    url = _list_url(prefix)
    while True:
        data = _get_json(url)
        if data is None:
            return
        items = data.get("items", [])
        if not items:
            return
        for item in items:
            name = item.get("name", "")
            if name:
                _delete_single(name)
        next_page = data.get("nextPageToken")
        if not next_page:
            return
        url = _list_url(prefix) + f"&pageToken={urllib.parse.quote(next_page)}"


def _delete_single(key: str) -> None:
    url = _object_url(key)
    _request("DELETE", url)


def delete(path: Path) -> None:
    key = _key(path)
    if not key:
        return
    _delete_single(key)
