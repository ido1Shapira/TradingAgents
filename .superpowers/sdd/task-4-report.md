# Task 4: Refactor storage.py — rename _gcs to _remote

## Status: DONE

## What I Implemented

Renamed all `_gcs` references to `_remote` in `web/server/storage.py`:

1. **Module docstring**: Updated GCS references → Firebase RTDB (FIREBASE_SERVICE_ACCOUNT/FIREBASE_DATABASE_URL)
2. **Module-level variable**: `_gcs` → `_remote`
3. **Init function**: `_init_gcs` → `_init_remote` (imports `firebase_rtdb` instead of `gcs`)
4. **Helper functions**: All five renamed (`_remote_path_exists`, `_remote_path_is_dir`, `_remote_iterdir`, `_remote_rmtree`, `_remote_mkdir`)
5. **All call sites**: Updated throughout (ticker_dir, ticker_runs_dir, create_run_dir, read_run, _find_run_dir, list_ticker_runs, find_resumable_run, delete_run, walk_data_dir, etc.)
6. **Warning messages**: All "GCS ..." → "Remote ..."
7. **Comment block**: Updated section header and description

## Tests

- **ruff check**: All checks passed
- **pytest**: 20/20 tests passed

## Files Changed

- `web/server/storage.py` (87 insertions, 86 deletions)

## Self-Review

- No remaining `_gcs` or `GCS` references in storage.py (verified via grep)
- Only remaining LSP error is pre-existing `total_seconds` type hint issue (line 324, unrelated)
- Followed exact patterns from the task brief for helper functions and `_init_remote`
- Warning messages consistently use "Remote" prefix

## Commit

- SHA: 1ed4383
- Message: refactor: rename _gcs to _remote in storage.py for Firebase RTDB
