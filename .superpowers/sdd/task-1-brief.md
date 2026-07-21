# Task 1: Add `firebase-admin` dependency

**Files:**
- Modify: `pyproject.toml`

**Interfaces:**
- Consumes: nothing
- Produces: `firebase-admin` available for import after `uv sync`

## Steps

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
