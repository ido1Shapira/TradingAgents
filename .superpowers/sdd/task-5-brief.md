# Task 5: Delete `gcs.py`

**Files:**
- Delete: `web/server/gcs.py`

**Interfaces:**
- Consumes: nothing
- Produces: nothing (module is removed)

## Steps

- [ ] **Step 1: Delete gcs.py**

```bash
git rm web/server/gcs.py
```

- [ ] **Step 2: Verify no remaining imports of gcs**

Run: `uv run python -c "from web.server import storage; print('OK')"`
Expected: `OK` (no ImportError)

- [ ] **Step 3: Run tests to verify no regressions**

Run: `uv run pytest web/server/tests/test_storage.py -v`
Expected: all tests PASS

- [ ] **Step 4: Commit**

```bash
git commit -m "chore: remove GCS storage backend (replaced by Firebase RTDB)"
```
