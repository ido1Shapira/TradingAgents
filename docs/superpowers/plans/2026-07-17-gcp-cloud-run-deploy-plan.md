# GCP Cloud Run Deploy Migration — Implementation Plan

Source spec: `docs/superpowers/specs/2026-07-17-gcp-cloud-run-deploy-design.md`
Branch: `feat/gcp-cloud-run-deployment` (already checked out)
Constraints: stay within GCP Always-Free tier; do not change application behavior; minimal scope per spec §7.

## Global Constraints (bind every task)

- All file paths are relative to repo root `C:\Users\Ido\Desktop\Projects\agents\TradingAgents`.
- Do NOT touch `web/server/storage.py`, `tradingagents/`, `cli/`, or any application logic. App behavior is unchanged (spec §7).
- Do NOT delete the Railway project; only remove the Railway config files from the repo (spec §5.1).
- Do NOT rewrite `cloud_persistence.py` to add GCS sync logic (spec §7, minimal scope). Just remove the Render API path and make the module a no-op for backup, with restore left as a no-op.
- Terraform project `trading-agent-9058` already exists and is applied — DO NOT modify its `project_id`, `region`, GCS bucket name, or service-account IDs.
- Commit style: follow the existing repo convention (`feat(scope): …`, `chore(scope): …`, `docs(scope): …`). One concern per commit. The repo's CI includes a mandatory version-bump check on PRs: bump the version in `pyproject.toml` AND `VERSION` together (run `uv run pytest -q` not needed for deploy-only changes; version bump is required for PR merge).
- LSP errors in `web/server/db_storage.py`, `storage.py`, `indicators.py`, `app.py` are pre-existing (SQLAlchemy-typing + pandas typing noise) and are NOT introduced by this work. Do not fix them.
- Use the project's uv venv: `uv run …` (see `AGENTS.md`).
- Bash is Windows PowerShell 5.1 — use proper PS syntax. The repo uses POSIX line endings for `.sh` files: preserve LF on `docker-entrypoint.sh` and `Dockerfile` (use `\n`, not `\r\n`).

## Pre-flight (Task 0)

- Confirm branch is `feat/gcp-cloud-run-deployment`.
- Confirm `terraform/terraform.tfstate` exists (already-applied state) — we will not run `terraform apply` ourselves; only edit `.tf` source for the `startup_cpu_boost` addition.
- Do not commit `terraform/*.tfstate*` or `terraform/.terraform/` — add to `.gitignore` first.

## Task 1: `.gitignore` — ignore terraform state & plugin cache

**Files:** `.gitignore`

**Changes:**
Append a new section at the end of `.gitignore`:
```
# Terraform state and provider cache (do not commit)
terraform/.terraform/
terraform/*.tfstate
terraform/*.tfstate.backup
terraform/.terraform.lock.hcl
```
Leave the existing `terraform/` directory untracked. Confirm with `git status` that `terraform.tfstate` and `.terraform.lock.hcl` and `.terraform/` show up as ignored (not in "Untracked files").

**Verification:**
- `git status` shows `terraform/` no longer under "Untracked files" (all sub-files now ignored).
- `git check-ignore -v terraform/terraform.tfstate` returns the rule.

**Commit:** `chore(terraform): ignore state files and provider cache`

## Task 2: Remove Railway config files

**Files to delete:**
- `railway.json`
- `railway-dashboard.md`
- `railway-frontend.md`
- `railway-prod-snapshot.md`

**Verification:**
- `git status --short` shows the four files as deleted.
- No code references to `railway.json` remain: `rg "railway.json" --glob '!*.md'` returns nothing.
- No code references to `RAILWAY_TOKEN`, `RAILWAY_API_KEY`, `railway up`, `Railway` (case-insensitive) in non-doc files outside terraform/README (those are handled in their own tasks): run `rg -i "railway" --glob '*.py' --glob '*.yml' --glob '*.yaml' --glob '*.json' --glob '*.sh'` and confirm only Django ignore-line `# ...` comments or wilderness remain — but the only allowed remaining: none in actual code.

**Commit:** `chore(deploy): remove Railway config and snapshot files`

## Task 3: Replace Railway CI deploy jobs with a Cloud Run deploy job

**Files:** `.github/workflows/ci.yml`

**Changes:**
- Delete the `deploy-dev` job (currently lines ~90–102 in the existing file).
- Delete the `deploy-prod` job (currently lines ~103–116).
- Add a new `deploy-cloud-run` job. See spec §6 for the YAML. Use GitHub **variables** (not secrets — these aren't sensitive) `GCP_PROJECT_ID`, `GCP_WORKLOAD_IDENTITY_PROVIDER`, `GCP_SERVICE_ACCOUNT_EMAIL`, `GCP_ARTIFACT_REGISTRY_REPO`. The job must:
  - `needs: [test, lint, smoke-install]` (NOT `version-check` — that is a PR-only gate)
  - Run only on push to `main` or `main-with-dashboard` (use the existing `if:` pattern from the old `deploy-prod` job, extended to both branches)
  - Top-level job `permissions: { contents: read, id-token: write }`
  - Steps: `actions/checkout@v4`, `google-github-actions/auth@v2` (WIF), `google-github-actions/setup-gcloud@v2`, configure-docker for `us-central1-docker.pkg.dev`, build + push tag `:sha-${short}` and `:latest`, `gcloud run deploy tradingagents --image=… --region=us-central1 --project=… --quiet --no-traffic` then `gcloud run services update-traffic tradingagents --to-latest --region=us-central1 --project=… --quiet`
- Leave the PR-only `deploy-dev` completely removed (we no longer have a Railway "staging" environment; PR previews are out of scope per spec §10).

**Verification:**
- `cat .github/workflows/ci.yml` shows no Railway references.
- YAML lint: `python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"` succeeds.
- `rg -i "railway" .github/` returns nothing.
- `rg "deploy-cloud-run" .github/` finds the new job name.
- Job uses `id-token: write` and `vars.GCP_*` (not `secrets.GCP_*`).

**Commit:** `ci(deploy): replace Railway deploy with Cloud Run via Workload Identity`

## Task 4: Harden the Dockerfile with a non-root user

**Files:** `Dockerfile`

**Changes:**
- After the `RUN mkdir -p /home/appuser/app && cp -r /build/. /home/appuser/app` line, add:
  ```dockerfile
  RUN useradd -r -u 1000 -g root appuser \
      && chown -R appuser:root /home/appuser/app /build
  USER appuser
  ```
  Place the `USER appuser` directive AFTER the `COPY docker-entrypoint.sh /docker-entrypoint.sh` and the `chmod +x` line, so the entrypoint remains readable/executable. The existing `chmod +x` may need a `chown` too — see verification.
- Preserve LF line endings (the file should already be LF; confirm with `git ls-files --eol Dockerfile`).
- Do not change the entrypoint or EXPOSE.

**Verification:**
- `docker build -t tradingagents:test .` succeeds (do not run if Docker not installed on this machine — the user may not have Docker locally; instead just inspect the Dockerfile).
- Confirm line endings: `git ls-files --eol Dockerfile` shows `i/lf` and `w/lf`.
- Confirm ordering: `USER appuser` is the last line before `ENTRYPOINT`.
- `docker-entrypoint.sh` still has `chmod +x` set as root before the user switch: `rg "USER appuser|chmod \+x /docker-entrypoint" Dockerfile` shows `chmod +x /docker-entrypoint.sh` comes BEFORE `USER appuser`.

**Commit:** `feat(docker): run container as non-root appuser for Cloud Run`

## Task 5: Add `startup_cpu_boost` to terraform

**Files:** `terraform/main.tf`

**Changes:**
- Inside the `template { ... }` block of `google_cloud_run_v2_service.main`, add a `startup_cpu_boost = true` property. (Terraform google provider supports this on `google_cloud_run_v2_service.template`.)
- Do not change any other field in `main.tf`.
- Do not run `terraform apply` from this task (avoid touching live infra during code review). Leave a note in the commit message that the user must run `terraform apply` after merge OR now to pick up the change.

**Verification:**
- `terraform fmt -check terraform/` passes (or `terraform fmt terraform/` makes no changes).
- `terraform validate terraform/` passes (requires Terraform CLI; skip if not installed).
- `rg "startup_cpu_boost" terraform/main.tf` finds the new line inside the `template { }` block.

**Commit:** `feat(terraform): enable Cloud Run startup CPU boost`

## Task 6: Strip the Render API path from `cloud_persistence.py`

**Files:** `web/server/cloud_persistence.py`

**Changes:**
- Remove imports no longer needed: `base64`, `urllib.request`.
- Remove the constants `BACKUP_ENV_VAR`, `WATCHLIST_FILE`, `RENDER_API_KEY`/`RENDER_SERVICE_ID` env-var reads (the `_api_key()` and `_service_id()` helpers).
- Rewrite `backup_watchlist()` to a no-op function preserving the existing signature `backup_watchlist(data_dir: str | Path) -> None`. Body: `log.debug("backup_watchlist is a no-op on Cloud Run (GCS mirroring not yet enabled)")`.
- Rewrite `restore_watchlist()` to a no-op preserving the signature `restore_watchlist(data_dir: str | Path) -> None`. Body: a single `log.debug("restore_watchlist is a no-op on Cloud Run (GCS mirroring not yet enabled)")` line. Do not attempt to read the GCS bucket — that's spec-out-of-scope.
- Update the module docstring to reflect: "On Cloud Run, the filesystem is ephemeral per spec §7 of the GCP deployment design. The Render env-var backup path is removed; future GCS sync is a separate spec."
- Keep `logging`, `os`, `json`, `Path` imports if still needed, else drop unused.
- Keep type hints intact. Do NOT change `app.py` or `queries.py` — they import and call these functions; no-op behavior is correct.

**Verification:**
- `uv run ruff check web/server/cloud_persistence.py` passes.
- `uv run pytest -q web/server/tests/` passes (existing storage/queries tests should be unaffected — confirm the suite runs green).
- `rg "RENDER_API_KEY|api.render.com|urllib" web/server/cloud_persistence.py` returns nothing.
- Module still imports cleanly: `uv run python -c "from web.server.cloud_persistence import restore_watchlist, backup_watchlist; restore_watchlist('x'); backup_watchlist('x'); print('ok')"` prints `ok`.

**Commit:** `refactor(persistence): remove Render env-var backup path; Cloud Run no-op`

## Task 7: Replace Railway deploy section in README with GCP runbook

**Files:** `README.md`

**Changes (this README was already modified on the branch to remove HF Spaces frontmatter — work in the current content):**
- Locate the existing "Deploy to Railway" / Railway section (likely missing since frontmatter was removed; if the README never had a deploy section, just APPEND a new one near the top after the title block).
- Add a new section titled `## Deploy to Google Cloud Run (free tier)`. Content from spec §5.3 and the GCP runbook skeleton:
  - Prereqs: `gcloud` CLI, a GCP project (`trading-agent-9058` configured), an适用于 OIDC workpool.
  - One-time bootstrap: `cd terraform && terraform init && terraform apply -var=project_id=trading-agent-9058 -var=github_owner=YOUR_GH_OWNER -var=github_repo=TradingAgents`. Read outputs.
  - Set GitHub repo variables (variables, not secrets — they're not sensitive): `GCP_PROJECT_ID`, `GCP_WORKLOAD_IDENTITY_PROVIDER`, `GCP_SERVICE_ACCOUNT_EMAIL`, `GCP_ARTIFACT_REGISTRY_REPO` (values from `terraform output`).
  - Set app secrets (LLM API keys) via `gcloud run services update tradingagents --region=us-central1 --update-env-vars OPENAI_API_KEY=...`.
  - Push to `main` → GitHub Actions `deploy-cloud-run` job builds/pushes image and deploys.
  - Free-tier caveats (per spec §4): Cloud Run scales to zero on idle; cold start <10s; egress to non-N.A. destinations is billable but in-budget for personal dashboard use.
  - Data persistence caveat: filesystem is ephemeral — past runs/watchlist reset on cold start. Future spec for GCS sync is referenced.
- Remove any `railway.json` mention. Replace Railway env-var examples with the GCP `gcloud run ... --update-env-vars` form.
- Do not delete the AGENTS.md note about uv venv — that stays.

**Verification:**
- `rg -i "railway" README.md` returns nothing (or only a histoylical footnote).
- The new "## Deploy to Google Cloud Run" anchor exists: `rg "^## Deploy to Google Cloud Run" README.md`.
- Markdown renders (no broken anchors): optional check, skip if no markdown linter configured.

**Commit:** `docs(readme): document Google Cloud Run deployment (free tier)`

## Task 8: Create the operator runbook `docs/deployment/gcp-cloud-run.md`

**Files:** `docs/deployment/gcp-cloud-run.md` (new directory + new file)

**Content:** See spec §5.3 — operator runbook with subsections:
- One-time bootstrap (gcloud login, terraform apply, read outputs).
- Set GitHub repo variables (explicit list with the four names).
- Setting app secrets via `gcloud run services update`.
- Manual redeploy (`gh workflow run` or merge a commit to `main`).
- Cost monitoring (GCP Console → Billing → Reports).
- Rollback (`gcloud run services update-traffic tradingagents --to-revision=REVISION_ID --region=us-central1`).
- Known limits of this migration (ephemeral filesystem, no GCS sync yet, no custom domain, no PR previews).

**Verification:**
- File exists at `docs/deployment/gcp-cloud-run.md`.
- `rg "WIF|workload_identity_provider|gcloud run services update-traffic" docs/deployment/gcp-cloud-run.md` finds the key command strings.

**Commit:** `docs(deploy): add GCP Cloud Run operator runbook`

## Task 9: Bump version for PR

**Files:** `pyproject.toml`, `VERSION`

**Changes:**
- Read current version: `git show origin/main:pyproject.toml | grep "^version"`. (If origin/main is unavailable, use the current branch's most-recent `main` ancestor: it's `0.3.1` per recent commits `chore: release v0.3.1`.)
- Bump the patch version: `0.3.1` → `0.3.2`. Update BOTH files in the same commit so the CI version-check job (`if (version_file != current_version)` exits 0).
- Use semantic-version-bump rules: a deploy migration is a maintenance chore, not a feature → patch bump only.

**Verification:**
- `grep "^version = " pyproject.toml` shows `version = "0.3.2"`.
- `cat VERSION` shows `0.3.2` (no trailing whitespace, no newline OR with trailing newline — match what was there).
- Diff: `git diff pyproject.toml VERSION` two-line diff.

**Commit:** `chore(release): bump version to 0.3.2`

## Final whole-branch review

After all 9 tasks:
- Push branch.
- Run CI locally? — can't (CI runs in GH Actions on push). Defer to the final reviewer's static pass + user's CI run after PR open.
- Run lint: `uv run ruff check web/` and `uv run pytest -q` to confirm we didn't break anything.
- Generate the review package: `git merge-base origin/main-with-dashboard HEAD` → `HEAD` and pass to the final code-reviewer subagent.
- Open PR: `gh pr create --base main-with-dashboard --head feat/gcp-cloud-run-deployment --title "Migrate deploy from Railway to Google Cloud Run (free tier)" --body-file <PR_BODY>`.

PR body sections:
- What changed
- Why GCP (free tier benefits, link to spec)
- New required GitHub repo variables (4 listed)
- Before-merge user checklist (set the 4 vars; optional `terraform apply` for startup_cpu_boost)
- Out-of-scope follow-ups (link spec §10)

## Done criteria

- All 9 tasks complete with clean per-task review.
- Final whole-branch review clean (or all findings triaged).
- PR opened; PR body includes the four GitHub repo variables the user must set.
- The user is left to: set the 4 GH repo variables, optionally `terraform apply`, merge.
