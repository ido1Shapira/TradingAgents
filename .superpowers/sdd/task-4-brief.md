# Task 4: Refactor `storage.py` — rename `_gcs` to `_remote`

**Files:**
- Modify: `web/server/storage.py`

**Interfaces:**
- Consumes: all 11 public functions from `firebase_rtdb.py` (Task 2)
- Produces: `init_settings()` calls `_init_remote()` which imports `firebase_rtdb`; all `_gcs_*` helpers renamed to `_remote_*`

## What to Change

This is a rename refactoring of `web/server/storage.py`. The file currently references a `gcs` module for remote storage. You need to:

1. **Update module docstring** (lines 1-12): Replace GCS references with Firebase RTDB references
2. **Rename module-level variable** `_gcs` → `_remote` (line 40)
3. **Replace `_init_gcs` function** (lines 63-79) with `_init_remote` that imports `firebase_rtdb` instead of `gcs`
4. **Update `init_settings`** (line 60): Call `_init_remote(data_dir)` instead of `_init_gcs(data_dir)`
5. **Rename all helper functions**:
   - `_gcs_path_exists` → `_remote_path_exists`
   - `_gcs_path_is_dir` → `_remote_path_is_dir`
   - `_gcs_iterdir` → `_remote_iterdir`
   - `_gcs_rmtree` → `_remote_rmtree`
   - `_gcs_mkdir` → `_remote_mkdir`
6. **Update all call sites** throughout the file (ticker_dir, ticker_runs_dir, create_run_dir, read_run, _find_run_dir, list_ticker_runs, find_resumable_run, delete_run, clear_ticker_data, walk_data_dir, etc.)
7. **Update all `_gcs and _gcs.is_enabled()` checks** to `_remote and _remote.is_enabled()`
8. **Update all `_gcs.read_json`, `_gcs.write_json`, etc.** to `_remote.read_json`, `_remote.write_json`, etc.
9. **Update fallback warning messages** from `"GCS ... failed"` to `"Remote ... failed"`

## Key Details

### New `_init_remote` function

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

### Helper function pattern

Each helper follows this pattern (example for `_remote_path_exists`):

```python
def _remote_path_exists(path: Path) -> bool:
    if _remote and _remote.is_enabled():
        try:
            return _remote.exists(path)
        except Exception:
            log.warning("Remote exists() failed for %s; falling back to local FS", path, exc_info=True)
    return path.exists()
```

### Call sites to update

Search for all occurrences of:
- `_gcs_path_exists` → `_remote_path_exists`
- `_gcs_path_is_dir` → `_remote_path_is_dir`
- `_gcs_iterdir` → `_remote_iterdir`
- `_gcs_rmtree` → `_remote_rmtree`
- `_gcs_mkdir` → `_remote_mkdir`
- `_gcs and _gcs.is_enabled()` → `_remote and _remote.is_enabled()`
- `_gcs.read_json` → `_remote.read_json`
- `_gcs.write_json` → `_remote.write_json`
- `_gcs.exists` → `_remote.exists`
- `_gcs.delete` → `_remote.delete`
- `_gcs.list_prefix` → `_remote.list_prefix`
- `"GCS ` → `"Remote ` (in warning messages)

## After Changes

1. Run: `uv run pytest web/server/tests/test_storage.py -v` (verify no regressions)
2. Run: `uv run ruff check web/server/storage.py` (verify lint clean)
3. Commit with message: `refactor: rename _gcs to _remote in storage.py for Firebase RTDB`
4. Report back with commit SHA and test results
