# Firebase Realtime Database Storage Backend

**Date:** 2026-07-20
**Status:** Approved (brainstormed)
**Owner:** Ido Shapira

## Goal

Replace the existing GCS storage backend with Firebase Realtime Database so the app can persist user data (watchlist, indicators, run history) across Cloud Run cold starts — without incurring any GCP charges. Keep the existing graceful-degradation pattern (remote backend → local filesystem fallback) so the app still works without Firebase configured.

## Why this change

- The app recently removed GCS because Cloud Storage Class A operations exceeded the free tier (~5K/month), costing ~NIS 0.02/month
- After the GCS removal the app uses Cloud Run's ephemeral filesystem; data resets on cold starts
- Firebase Realtime Database (Spark plan, no credit card) offers generous limits that fit our usage:
  - 1 GB storage
  - 10 GB/month egress
  - 100 concurrent connections
  - No cost until the "Blaze" plan is enabled (it isn't)
- Firebase RTDB suits our workload: small JSON files (watchlist, indicators, run metadata) plus append-only event logs

## Scope

In scope:
- Add `web/server/firebase_rtdb.py` — new backend module mirroring `gcs.py`'s interface
- Modify `web/server/storage.py` — rename `_gcs_*` to `_remote_*`, replace `_init_gcs` with `_init_remote`
- Update CI workflow smoke test: swap `GCS_BUCKET` env var for `FIREBASE_SERVICE_ACCOUNT`
- Update `docs/deployment/gcp-cloud-run.md` with Firebase setup instructions
- Add `firebase-admin` to `pyproject.toml` dependencies
- Add a free-tier guard inside Firebase RTDB writes that prevents exceeding the 20K writes/day cap
- Add a repository rule to `AGENTS.md`: "All GCP services used by this app must stay on the free tier"

Out of scope (deferred to future work):
- Migrating the existing `web/server/gcs.py` module (it will be deleted once this lands)
- Realtime listeners — the app polls, not subscribes
- Offline caching on the client (irrelevant — the Admin SDK has no offline mode)
- Firestore (different product, different quotas)

## Design

### Architecture

```
┌─────────────────────────────┐
│  web/server/app.py          │
│  (FastAPI endpoints)        │
└─────────────┬───────────────┘
              │ calls
              ▼
┌─────────────────────────────┐
│  web/server/storage.py      │  ← Public API: write_json_atomic,
│  (abstraction layer)        │    read_json, append_jsonl, etc.
└──────┬──────────────┬───────┘
       │ tries         │ falls back to
       ▼               ▼
┌──────────────┐  ┌─────────────────┐
│ firebase_    │  │ local /data/    │
│ rtdb.py      │  │ ephemeral FS    │
│ (new module) │  │                 │
└──────┬───────┘  └─────────────────┘
       │
       ▼
┌──────────────────────────────┐
│  Firebase Realtime Database  │
│  (Spark plan, free)          │
└──────────────────────────────┘
```

`storage.py` keeps the existing "remote → local fallback" pattern. Every remote call is wrapped in try/except; on failure the call falls through to local filesystem writes and logs a WARNING. This is unchanged from the GCS backend's behaviour.

### Firebase RTDB schema

Filesystem paths are translated to RTDB paths by replacing directory separators:

```
Local path                                        RTDB node
─────────────────────────────────────────────────   ───────────────────────────────────────────
/data/NVDA/2026-07-20/run-1714-IDT/run.json       /data/NVDA/2026-07-20/run-1714-IDT/meta
/data/NVDA/2026-07-20/run-1714-IDT/events.jsonl   /data/NVDA/2026-07-20/run-1714-IDT/events   (list)
/data/NVDA/2026-07-20/run-1714-IDT/llm_calls.jsonl /data/NVDA/2026-07-20/run-1714-IDT/llm_calls (list)
/data/NVDA/2026-07-20/run-1714-IDT/stages/market.json
                                                  /data/NVDA/2026-07-20/run-1714-IDT/stages/market
/data/watchlist.json                             /data/_watchlist   (singleton object)
/data/indicators.json                            /data/_indicators  (singleton object)
/data/notifier.json                              /data/_notifier    (singleton object)
```

**Rules:**
- Characters that are illegal in RTDB keys (`.`, `#`, `$`, `[`, `]`, `/`) are replaced with `_` in segment names. The `/` we keep only as the RTDB path separator between segments.
- JSON files map to RTDB **objects** (key:value trees)
- Append-only JSONL files (`events.jsonl`, `llm_calls.jsonl`) map to RTDB **lists** written with `push()` so each append gets a unique auto-ordered key. Reads reconstruct the list by sorting keys (push key order = chronological order on RTDB).
- Binary files (e.g. SQLite checkpoints at `cache/checkpoints/{TICKER}.db`) stay on local FS — RTDB is JSON-only.

### Module interface: `firebase_rtdb.py`

Mirrors `gcs.py`'s contract exactly so `storage.py`'s call sites don't need to change beyond rename.

```python
def init(creds_json_str: str, database_url: str, data_root: str) -> None:
    """Initialise Firebase Admin SDK. Idempotent. Fails gracefully."""

def is_enabled() -> bool:
    """True after a successful init()."""

def read_json(path: Path) -> Any | None:
    """Return parsed JSON at RTDB node, or None if missing."""

def write_json(path: Path, data: Any) -> None:
    """Replace RTDB node with data. Creates parents automatically."""

def append_jsonl(path: Path, obj: Any) -> None:
    """Push obj onto RTDB list. Atomic."""

def read_jsonl(path: Path) -> list[Any]:
    """Return all entries in RTDB list in insertion order."""

def exists(path: Path) -> bool:
    """True if RTDB node exists OR has any child keys."""

def is_dir(path: Path) -> bool:
    """True if RTDB node has any child keys."""

def list_prefix(path: Path) -> list[str]:
    """Return sorted immediate child key names under RTDB node."""

def delete_prefix(path: Path) -> None:
    """Recursively delete RTDB node and all children."""

def delete(path: Path) -> None:
    """Delete a single RTDB node."""
```

### Behaviour differences from `gcs.py`

| Operation | GCS behaviour | Firebase RTDB behaviour |
|---|---|---|
| `append_jsonl` | Read full file + write (racy under multicontainer deploys) | `ref.push(data)` — atomic, race-free |
| `is_dir` | Issues a list query with `maxResults=1` | Reads `shallow=True` snapshot |
| `list_prefix` | Issues a paginated list query | Reads `shallow=True` snapshot |
| `delete_prefix` | Loops with `pageToken` | Single recursive `delete()` |
| Path with `..` or `~` | Forbidden by GCS keys | Forbidden by RTDB keys; rejected |

### Free-tier guards

`firebase_rtdb.py` tracks the daily write count in memory. When a write approaches the 20K/day cap (default 18,000 = 90%), it logs a WARNING and falls through to local FS for that write. The counter resets at UTC midnight.

`storage.py`'s existing fallback warning ("GCS write_json() failed... falling back to local FS") is renamed to a generic message ("remote write failed... falling back to local FS") so logs aren't misleading.

### Authentication

- `FIREBASE_SERVICE_ACCOUNT` env var: a base64-encoded JSON service account key
- `FIREBASE_DATABASE_URL` env var: e.g. `https<area>://<project-id>-default-rtdb.firebaseio.com/`
- `init()` decodes the base64 creds, calls `firebase_admin.initialize_app(cred, {'databaseURL': ...})`
- After init: `_db = firebase_admin.db` — all reads/writes go through `firebase_admin.db.reference(...)`
- Re-init safe: subsequent `init()` calls are no-ops if already initialised
- All reads/writes have a 10-second timeout (they are blocking calls from uvicorn handlers)

### Smoke test change

In `.github/workflows/ci.yml` the existing `GCS_BUCKET=tradingagents-smoke-test-nonexistent` env var is replaced with `FIREBASE_SERVICE_ACCOUNT=fake` + `FIREBASE_DATABASE_URL=fake`. Both decode/parse failure is expected: the fallback is exercised, the app still starts.

### Deployment additions

New secrets/variables (none required for free-tier, but needed for runtime auth):

- GitHub repo secret: `FIREBASE_SERVICE_ACCOUNT` (base64 of service account JSON key)
- GitHub repo secret: `FIREBASE_DATABASE_URL` (RTDB URL)
- Cloud Run env vars (added by the existing CI env-vars step):
  - `FIREBASE_SERVICE_ACCOUNT=${{ secrets.FIREBASE_SERVICE_ACCOUNT }}`
  - `FIREBASE_DATABASE_URL=${{ secrets.FIREBASE_DATABASE_URL }}`
- The CI deploy step removes any prior `GCS_BUCKET` env var (clean migration)
- Firebase Database rules (set in Firebase Console once at setup, never again):
  ```json
  { "rules": { ".read": "auth != null", ".write": "auth != null" } }
  ```

### Free-tier constraint table

| Resource | Free tier | Expected usage (personal) |
|---|---|---|
| RTDB storage | 1 GB | ~10 MB (many runs) |
| RTDB downloads | 10 GB/month | ~100 MB/month |
| RTDB writes | 20K/day | ~5K/day typical; guard at 18K/day |
| RTDB reads | 50K/day | ~10K/day typical |
| Concurrent connections | 100 | 1 (single Cloud Run instance) |

The guard at 18K writes/day is the only enforcement. All other limits are document-only (no guard code needed).

## Test plan

Unit tests (`web/server/tests/test_firebase_rtdb.py`):
- Mock `firebase_admin.db.reference` with a fake tree that supports get/set/push/delete
- Test each of the 11 interface functions against the fake
- Test the daily-write guard threshold by mocking the counter
- Test init's behaviour on bad creds (graceful failure, is_enabled returns False)

Integration tests (optional, manual):
- Deploy with a real Firebase project, run a full pipeline, verify data persists across cold starts
- Trigger an instance scale-up, check no race conditions in append_jsonl

CI:
- Smoke test job: ensure the app starts with `FIREBASE_SERVICE_ACCOUNT=fake`, falls back to local FS, all API endpoints return 200
- This exercises the same code path (graceful fallback) that the GCS smoke test did

## Migration / rollout

One-shot migration (this PR):
1. Create Firebase project & RTDB (one-time)
2. Generate service account JSON key (one-time)
3. Add `FIREBASE_SERVICE_ACCOUNT` and `FIREBASE_DATABASE_URL` to GitHub repo secrets
4. Land the code changes via the standard PR → CI → merge → deploy flow
5. Verify on Cloud Run: data persists after `--min-instances=0` cold start

Rollback (if needed):
- Delete the firebase_rtdb.py module
- Revert storage.py to the GCS path-agnostic version (which still falls back to local FS)
- The CI smoke test reverts to using GCS_BUCKET=fake

## Impact

| Item | Change |
|---|---|
| Dependencies | +`firebase-admin` (~5 lines in pyproject.toml) |
| Image size | 852 MB → ~930 MB (≈+80 MB from firebase-admin and its deps) |
| Cloud Run cost | Unchanged (free tier) |
| GCP cost | Removed: Artifact Registry + Cloud Storage charges; Added: zero (Spark plan) |
| Cloud Run service | Same env vars minus `GCS_BUCKET`, plus the two new FIREBASE_* vars |
| Terraform | No change (we already removed GCS earlier) |
| Tests | New unit test file `test_firebase_rtdb.py` |

## Open questions

None — answered during brainstorming.
