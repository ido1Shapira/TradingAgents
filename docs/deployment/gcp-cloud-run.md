# Operator Runbook — Google Cloud Run Deployment

This runbook covers everything an operator needs to bootstrap, deploy, roll
back, and cost-monitor the TradingAgents dashboard on Google Cloud Run,
free-tier only.

Source spec: [`docs/superpowers/specs/2026-07-17-gcp-cloud-run-deploy-design.md`](../superpowers/specs/2026-07-17-gcp-cloud-run-deploy-design.md)

## 1. Prerequisites

- A GCP organization with billing attached (required even for Always-Free;
  GCP will not bill $0 resources but needs a billing account on file).
- The `gcloud` CLI installed and authenticated:
  ```bash
  gcloud auth login
  gcloud config set project trading-agent-9058
  ```
- Terraform >= 1.5 installed locally.
- The GitHub repo has been bound to the Workload Identity Federation provider
  via terraform (`google_iam_workload_identity_pool_provider.github`).

## 2. One-time bootstrap

The terraform stack in `terraform/` has already been applied to
`trading-agent-9058` (state file is `.gitignore`d and lives on the operator's
machine; back it up by copying the local `terraform/terraform.tfstate` to a
private GCS bucket if it is not already there).

To apply (idempotent — only re-applying after this PR adds
`startup_cpu_boost = true`):

```bash
cd terraform
terraform init
terraform apply \
  -var=project_id=trading-agent-9058 \
  -var=github_owner=<your-github-handle> \
  -var=github_repo=TradingAgents
```

Read the outputs and set them as GitHub repo **variables** (NOT secrets —
these are not sensitive — they are public identifiers used by OIDC):

```bash
terraform output workload_identity_provider
terraform output deploy_service_account_email
terraform output artifact_registry_repo
terraform output cloud_run_url
terraform output gcs_bucket_name
```

In the GitHub web UI (Settings → Secrets and variables → Actions → Variables
tab), add:

| Variable | Value |
|---|---|
| `GCP_PROJECT_ID` | `trading-agent-9058` |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | value of `terraform output workload_identity_provider` |
| `GCP_SERVICE_ACCOUNT_EMAIL` | value of `terraform output deploy_service_account_email` |
| `GCP_ARTIFACT_REGISTRY_REPO` | value of `terraform output artifact_registry_repo` |

After these are set, the next push to `main` (or `main-with-dashboard`) will
trigger the `deploy-cloud-run` GitHub Actions job.

## 3. Setting app secrets (LLM API keys, etc.)

App env vars are set automatically by the CI/CD deploy job. They are stored
as GitHub Actions **secrets** (one per key) and passed to Cloud Run via
`gcloud run services update --update-env-vars` after every deploy.

To add or update a secret:

1. Add it in GitHub (Settings → Secrets and variables → Actions → New
   repository secret).
2. Add the `${{ secrets.YOUR_KEY }}` reference to
   `.github/workflows/ci.yml` in the `Set environment variables` step.
3. Push — the next CI run will propagate it.

> The old `gcloud run services update --update-env-vars` hand-roll is no
> longer needed; the CI pipeline handles it.

## 4. Redeploying

- **Automatic:** merge (or push) to `main` → GitHub Actions runs tests, lints,
  and if all green, the `deploy-cloud-run` job builds the image and rolls the
  service forward.
- **Manual:** trigger the workflow from the GitHub Actions UI (`gh workflow
  run ci.yml` or click "Run workflow"), or push an empty commit to `main`.

## 5. Rollback

Cloud Run keeps the last several revisions. To roll back:

```bash
# List recent revisions
gcloud run revisions list --service=tradingagents --region=us-central1

# Route 100% of traffic to a previous revision
gcloud run services update-traffic tradingagents \
  --to-revision=<REVISION_NAME> \
  --region=us-central1
```

The next push that succeeds will bring traffic back to `LATEST`.

## 6. Cost monitoring

- GCP Console → **Billing** → **Reports** — group by Service to see Cloud
  Run, Artifact Registry, and Cloud Storage line items.
- Expected monthly spend: $0 for personal dashboard use.
  - Cloud Run: free up to 2M requests, 360k vCPU-sec, 180k MiB-sec/month.
  - Artifact Registry: 0.5GB free; one image runs ~600MB so we are at the
    edge if many tags accumulate. Old image tags are NOT auto-deleted; see
    "Maintenance" below.
  - GCS Standard bucket: 5GB free; currently nearly empty (no data mirroring
    yet).

If costs creep up unexpectedly, the usual culprits:

1. Sustained traffic from non-N.A. regions (egress billed outside Always-Free).
2. Old Artifact Registry image tags — clean them with:
   ```bash
   gcloud artifacts docker images list \
     us-central1-docker.pkg.dev/trading-agent-9058/tradingagents-images --include-tags
   gcloud artifacts docker images delete <image>@<digest>
   ```
3. `min_instance_count` was bumped above 0 — keep at 0 to use free tier.

## 7. Known limits of this migration

These are explicit out-of-scope follow-ups (see spec §10):

- **Ephemeral filesystem:** past runs, watchlist, and indicators reset on
  every cold start. A GCS storage backend (`web/server/gcs.py`) is now wired
  into `storage.py` — when `GCS_BUCKET` is set (it is on Cloud Run), all IO
  reads from and writes to GCS, surviving cold starts.
- **No Secret Manager integration:** LLM API keys live in GitHub Actions
  secrets and are passed to Cloud Run as env vars. Rotating a key means
  updating the GitHub secret and pushing.
- **No custom domain:** the dashboard is reachable at
  `https://tradingagents-<hash>-uc.a.run.app` only. Adding a custom domain
  is a future spec.
- **No PR-preview deploys:** only pushes to `main` / `main-with-dashboard`
  deploy. A future spec may add a `tradingagents-staging` Cloud Run service
  for PR previews.
- **No VPC connector / private network:** the service uses direct public
  ingress per `INGRESS_TRAFFIC_ALL`.

## 8. Troubleshooting

**First deploy (`deploy-cloud-run` job) fails on `gcloud run deploy`:**
- Confirm the four GitHub repo variables are set with the correct values
  from `terraform output`.
- Confirm your GitHub repo is set as `attribute.repository` on the WIF
  provider (the terraform stack does this with `var.github_owner` /
  `var.github_repo`).
- Run locally with the deploy SA key (download a key via
  `gcloud iam service-accounts keys create` to test) — the WIF path should
  yield the same IAM permissions; if a permission error appears, grant the
  missing role to `tradingagents-deploy@…`.

**Cloud Run revision fails startup probe (`/api/health`):**
- Cloud Run logs: `gcloud run services logs read tradingagents --region=us-central1`
- Common cause: missing required env var (e.g., `AUTH_DISABLED=true` is
  required to start without a login form — set in the CI/CD env-vars step).
- The new revision will not receive traffic while it is unhealthy. Existing
  latest-healthy revision keeps serving.

**Cold-start takes >10s:**
- Check that `startup_cpu_boost` is set (should be on after terraform apply
  post-merge). Confirm via `gcloud run services describe tradingagents
  --region=us-central1 --format="value(spec.template.startup_cpu_boost)"`.

## 9. Maintenance

- Terraform state lives locally. Back it up to a private GCS bucket:
  ```bash
  gsutil mb -p trading-agent-9058 -l us-central1 -b on \
    gs://trading-agent-9058-tfstate
  gsutil cp terraform/terraform.tfstate \
    gs://trading-agent-9058-tfstate/terraform.tfstate
  ```
- Prune old Artifact Registry tags monthly (see §6 step 2).
- Periodically rebuild the Docker base image: edit `Dockerfile` base image
  version (currently `python:3.12-slim`) and rebuild/push via CI.

## 10. Glossary

- **WIF** — Workload Identity Federation. Lets GitHub Actions mint a
  short-lived GCP access token via OIDC, without storing a long-lived GCP
  service-account JSON key in GitHub secrets.
- **Revision** — an immutable snapshot of the Cloud Run service config
  plus its image; the unit of traffic routing and rollback.
- **Always-Free tier** — A monthly per-project free quota on participating
  GCP services. Subject to change — verify the current limits at
  https://cloud.google.com/free.
