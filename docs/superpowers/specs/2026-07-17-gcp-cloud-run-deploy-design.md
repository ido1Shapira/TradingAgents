# GCP Cloud Run Deployment Migration — Design

- **Date:** 2026-07-17
- **Status:** Approved by user
- **Branch:** `feat/gcp-cloud-run-deployment` (existing; terraform already applied to project `trading-agent-9058`)
- **Scope goal:** Switch the deployment framework from Railway to Google Cloud Run, staying within GCP Always-Free tier limits. Application behavior unchanged.

## 1. Context

The project is a Python/FastAPI dashboard (`web/server/app.py`) serving a bundled React SPA, deployable from a single `Dockerfile`. Today it deploys to Railway via `railway.json` + two `ci.yml` deploy jobs (`deploy-dev`, `deploy-prod`) using `RAILWAY_TOKEN_*` secrets.

A prior session partially started GCP work on branch `feat/gcp-cloud-run-deployment`:

- `terraform/` directory with `main.tf`, `variables.tf`, `outputs.tf`, `provider.tf`, `versions.tf`
- Terraform already applied to live GCP project `trading-agent-9058`:
  - Artifact Registry repo `tradingagents-images` in `us-central1`
  - GCS bucket `tradingagent-data-files-trading-agent-9058` (Standard, 5GB free)
  - Cloud Run service `tradingagents` (512Mi, 1000m CPU, min 0 / max 2 instances)
  - Service accounts `tradingagents-cloud-run` and `tradingagents-deploy`
  - Workload Identity Federation pool/provider + GitHub repo binding
  - Public unauthenticated invoker IAM on the Cloud Run service
- `pyproject.toml` adds `google-cloud-storage>=2.16.0`
- `README.md` had HuggingFace Spaces frontmatter removed (per-file diff)

Not yet done:

- `ci.yml` still has Railway deploy jobs; no Cloud Run deploy job exists
- `railway.json`, `railway-*.md` files still in repo
- `Dockerfile` not hardened (no `USER appuser`)
- `cloud_persistence.py` still uses Render API (`RENDER_API_KEY` / `RENDER_SERVICE_ID`) — broken on Cloud Run
- No operator runbook
- `terraform/*.tfstate*` not in `.gitignore` (state file lives in working tree)
- No `startupCPUBoost` enabled

## 2. User-confirmed decisions

| Decision | Choice |
|---|---|
| Free-tier strategy | Cloud Run only (no GCE VM, no hybrid) |
| Region | `us-central1` (current; Always-Free eligible) |
| Deploy trigger | GitHub Actions via Workload Identity Federation |
| Railway cleanup | Delete `railway.json` + disable Railway deploy jobs in `ci.yml` |
| Data persistence scope | Minimal — accept ephemeral filesystem. Past runs/config/watchlist reset on cold start. (Future: GCS mirroring is a separate feature.) |

## 3. Architecture

```
GitHub repo push (main)
      │
      ▼
GitHub Actions CI (existing: test, lint, smoke-install, version-check)
      │
      ▼ (needs: CI green)
deploy-cloud-run job:
      ├── oidc-login-gcp (WIF mint creds → short-lived GCP token)
      ├── docker/auth to Artifact Registry
      ├── docker/build   → us-central1-docker.pkg.dev/{project}/tradingagents-images/app:{sha}
      ├── docker/push    to Artifact Registry
      └── gcloud run deploy tradingagents --image=... --region=us-central1
                │
                ▼
        Cloud Run service `tradingagents` (single revision, traffic=100% LATEST)
                │
                ▼
        HTTPS endpoint: https://tradingagents-{hash}-uc.a.run.app
```

- Container runtime contract honored: listens on `$PORT` (=8000, set via terraform env), `/api/health` for startup/liveness probes (already in terraform).
- No Claude/GCP service-account JSON keys in GitHub. WIF is bound via:
  `google_service_account_iam_member.deploy_workload_identity_user` →
  `principalSet://iam.googleapis.com/{pool}/attribute.repository/{owner}/{repo}`
- Public unauthenticated invoker (`allUsers`) preserves Railway's "anyone-with-the-URL-can-reach" behavior.

## 4. Free-tier budget (per-month projection)

| Resource | Always-Free allowance | Expected personal usage | Status |
|---|---|---|---|
| Cloud Run requests | 2 M / month | <100 k | OK |
| Cloud Run vCPU-sec | 360 k | <10 k | OK |
| Cloud Run MiB-sec | 180 k (with 512 Mi = ~360 k sec) | cold start a few times/day | OK |
| Cloud Run egress (N.A. dest) | 200 MB / request, generous monthly | dashboard JSON ≪ | OK |
| Artifact Registry storage | 0.5 GB | <1 GB (one image) | OK |
| GCS Standard storage | 5 GB | ~0 (no mirroring yet) | OK |
| Secret Manager | free for 6 active versions per secret | unused this round | OK |

**Caveat:** Egress to non-N.A. destinations (Asia/Australia) is NOT always-free. Since `region=us-central1`, traffic from outside N.A. is billed. For personal dashboard use this stays well under billable thresholds; for production-traffic patterns the user should enable a CDN or move to multi-region.

## 5. Component changes

### 5.1 Files to delete
- `railway.json`
- `railway-dashboard.md`
- `railway-frontend.md`
- `railway-prod-snapshot.md`

### 5.2 Files to edit

**`.github/workflows/ci.yml`**
- Remove `deploy-dev` (Lines 90–102) and `deploy-prod` (Lines 103–116) jobs that use Railway CLI.
- Add a new `deploy-cloud-run` job that:
  - Runs on push to `main` / `main-with-dashboard` after `needs: [test, lint, smoke-install]`
  - Uses `google-github-actions/auth@v2` with WIF (`workload_identity_provider`, `service_account`, plus the `id_token: true` permission on the job)
  - Uses `docker/login-action@v3` with `google` password helper to access Artifact Registry (`us-central1-docker.pkg.dev`)
  - Builds via `docker build -t {repo}/app:{sha} .` and pushes
  - Invokes `gcloud run deploy tradingagents --image={...} --region=us-central1 --project=${{ vars.GCP_PROJECT_ID }} --no-traffic --source` removed; uses `--image` only, plus `--quiet`
  - (Optional) `--tag=sha-XYZ` for traceability
  - Sets traffic 100% on the new revision via `gcloud run services update-traffic tradingagents --to-latest --region=us-central1`
- Keep `version-check`, `test`, `lint`, `smoke-install` jobs as-is.

**`Dockerfile`**
- Add a non-root user:
  ```dockerfile
  RUN useradd -r -u 1000 -g root appuser && \
      chown -R appuser:root /home/appuser
  USER appuser
  ```
- Reduce image size opportunistically: skip the `curl` removal step is fine; the existing multi-stage cleanup is already reasonable. No major reorganization.
- No other behavioral changes (entrypoint already does `mkdir -p $TRADINGAGENTS_DATA_DIR`).

**`terraform/main.tf`**
- Add `startup_cpu_boost = true` to the `template { ... }` block (free-tier OK; only boosts cold starts, not steady-state billing).
- Cloud Run service env is consistent. `PORT=8000`, `TRADINGAGENTS_DATA_DIR=/data`, `TRADINGAGENTS_CACHE_DIR=/data/cache`, `AUTH_DISABLED=true`. Keep `TRADINGAGENTS_API_RATE_LIMIT=30/minute`.
- Leave `GCS_BUCKET` env wired (unused by app code today; reserved for future persistence work).

**`terraform/variables.tf` / `outputs.tf`**
- No new variables needed. Outputs already expose `cloud_run_url`, `workload_identity_provider`, `deploy_service_account_email`, `gcs_bucket_name`, `artifact_registry_repo`.

**`web/server/cloud_persistence.py`**
- Remove the Render API path (`_api_key`, `_service_id`, `BACKUP_ENV_VAR`, the HTTP PUT to `api.render.com/v1/services/.../env-vars`).
- Replace `backup_watchlist()` with a no-op (when no GCS-style backup configured). Restore remains a no-op (consistent with minimal-scope decision; the GCS bucket env is wired but we are NOT writing the GCS sync logic in this round).
- Keep the function signatures intact so `app.py` / `queries.py` callers don't change. Update the module docstring to reflect the change.

**`README.md`**
- Replace Railway deployment section with a GCP section: prerequisites (`gcloud` CLI auth), one-time `terraform init && terraform apply`, required GitHub Actions variables (`GCP_PROJECT_ID`, `GCP_WORKLOAD_IDENTITY_PROVIDER`, `GCP_SERVICE_ACCOUNT_EMAIL`, `GCP_ARTIFACT_REGISTRY_REPO`), and the "push to main → deploys automatically" message.
- Mention free-tier cost expectations.

**`.gitignore`**
- Add (if not present):
  ```
  terraform/.terraform/
  terraform/*.tfstate
  terraform/*.tfstate.backup
  ```

### 5.3 Files to create

**`docs/deployment/gcp-cloud-run.md`** (operator runbook)
- One-time bootstrap:
  1. `gcloud auth login`
  2. `cd terraform && terraform init && terraform apply -var=project_id=trading-agent-9058 -var=github_owner=… -var=github_repo=TradingAgents`
  3. Read outputs: `terraform output workload_identity_provider deploy_service_account_email cloud_run_url`
  4. Set GitHub Actions repo variables (not secrets — these aren't sensitive):
     - `GCP_PROJECT_ID`
     - `GCP_WORKLOAD_IDENTITY_PROVIDER`
     - `GCP_SERVICE_ACCOUNT_EMAIL`
     - `GCP_ARTIFACT_REGISTRY_REPO`
- Setting app-level secrets (LLM API keys etc.):
  - Via `gcloud run services update tradingagents --region=us-central1 --update-env-vars OPENAI_API_KEY=…`
  - (Or: optional Secret Manager migration — out of scope here)
- Redeploying manually:
  - `gh workflow run deploy.yml` or push to main
- Cost monitoring link: GCP Console → Billing → Reports
- How to roll back: `gcloud run services update-traffic tradingagents --to-revision=REVISION_ID --region=us-central1`

## 6. GitHub Actions auth flow

```yaml
permissions:
  contents: read
  id-token: write   # required for OIDC

jobs:
  deploy-cloud-run:
    needs: [test, lint, smoke-install]
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: ${{ vars.GCP_WORKLOAD_IDENTITY_PROVIDER }}
          service_account: ${{ vars.GCP_SERVICE_ACCOUNT_EMAIL }}
      - uses: google-github-actions/setup-gcloud@v2
      - name: Configure Docker for Artifact Registry
        run: gcloud auth configure-docker us-central1-docker.pkg.dev --quiet
      - name: Build & push image
        run: |
          TAG=${GITHUB_SHA::7}
          IMAGE="${{ vars.GCP_ARTIFACT_REGISTRY_REPO }}/app:${TAG}"
          docker build -t "$IMAGE" .
          docker push "$IMAGE"
          echo "IMAGE=$IMAGE" >> $GITHUB_ENV
      - name: Deploy to Cloud Run
        run: |
          gcloud run deploy tradingagents \
            --image="$IMAGE" \
            --region=us-central1 \
            --project="${{ vars.GCP_PROJECT_ID }}" \
            --quiet \
            --no-traffic
          gcloud run services update-traffic tradingagents \
            --to-latest \
            --region=us-central1 \
            --project="${{ vars.GCP_PROJECT_ID }}" \
            --quiet
```

`main-with-dashboard` branch: optionally add the same job for the secondary branch. We'll keep the deploy restricted to `main` only to reduce churn; user can add a second branch later.

## 7. Data persistence — explicit non-goals (this PR)

We are NOT changing these in this migration (per user decision "minimal"):

- `web/server/storage.py` file-based read/write paths
- Adding GCS-backed run/event persistence
- Migrating `.env` config to Secret Manager
- Mirroring watchlist to GCS (we just no-op the Render hack)
- Adding a Cloud Storage FUSE volume mount to Cloud Run

**Known consequence:** any past runs created on Cloud Run disappear on instance cold-start (every ~15 min of inactivity). This is acceptable for now and is documented in the README runbook. Persistent storage is a separate follow-up spec.

## 8. Risk & rollback

- **Railway untouched during the migration**: per decision, we delete `railway.json` from this branch but do not delete the Railway project or its secrets. The user can continue running the Railway deployment until Cloud Run is verified, then manually tear down Railway.
- **Terraform change is forward-only**: `terraform apply` will add `startup_cpu_boost` to the next service revision; existing revision keeps traffic until CI deploys the new image. Safe.
- **Failing CI deploy**: the GitHub Actions step keeps `--no-traffic` then `update-traffic --to-latest`. If `gcloud run deploy` succeeds but the new revision fails the health probe, `update-traffic` won't be reached → existing revision stays live. Safe-by-default.
- **First deploy fails entirely**: user can fall back to Railway until diagnosis.

## 9. Verification checklist (to be exercised after implementation)

1. `terraform apply` runs clean against `trading-agent-9058` with only `startup_cpu_boost` diff.
2. CI green on the branch (tests, lint, smoke-install).
3. First push to main triggers `deploy-cloud-run` job; succeeds within ~3 minutes.
4. `gcloud run services describe tradingagents --region=us-central1` shows `status: CONDITIONS_READY`.
5. `https://tradingagents-..-uc.a.run.app/api/health` returns `{"status":"ok", ...}`.
6. Dashboard loads at the Cloud Run URL; watchlist add/remove works (writes persist for the instance lifetime).
7. Cloud Run scales to zero after idle; first cold-start request completes within <10s (startup CPU boost helps).
8. Cloud Billing Reports shows $0 incremental spend for the day.

## 10. Out-of-scope follow-ups (named for future planning)

- Spec: persistent storage on GCP for past runs (incremental file mirror or Cloud SQLite).
- Spec: Secret Manager migration for app LLM keys.
- Spec: custom domain + managed TLS via Cloud Domains.
- Spec: PR-preview deploys to a separate Cloud Run service (`tradingagents-staging`).
