resource "google_project_service" "apis" {
  for_each = toset([
    "run.googleapis.com",
    "iamcredentials.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "secretmanager.googleapis.com",
  ])
  service            = each.key
  disable_on_destroy = false
}

# Cloud Run service account
resource "google_service_account" "cloud_run" {
  account_id   = "tradingagents-cloud-run"
  display_name = "TradingAgents Cloud Run service account"
}

resource "google_project_iam_member" "cloud_run_secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.cloud_run.email}"
}

# Cloud Run service (single shared deployment; staging prefix removed to keep free)
resource "google_cloud_run_v2_service" "main" {
  name                = "tradingagents"
  location            = var.region
  ingress             = "INGRESS_TRAFFIC_ALL"
  deletion_protection = false

  template {
    service_account = google_service_account.cloud_run.email
    containers {
      image = "ghcr.io/ido1shapira/tradingagents/app:latest"
      ports {
        container_port = 8000
      }

      resources {
        limits = {
          memory = var.cloud_run_memory
          cpu    = var.cloud_run_cpu
        }
        startup_cpu_boost = true
      }

      # Free-tier-friendly startup
      startup_probe {
        http_get {
          path = "/api/health"
          port = 8000
        }
        initial_delay_seconds = 10
        period_seconds        = 10
        failure_threshold     = 15
      }
      liveness_probe {
        http_get {
          path = "/api/health"
          port = 8000
        }
        period_seconds    = 30
        failure_threshold = 3
      }

      # PORT is auto-set by Cloud Run (do not set it here — GCP rejects the
      # reserved name with "The following reserved env names were provided: PORT").
      env {
        name  = "TRADINGAGENTS_DASHBOARD_HOST"
        value = "0.0.0.0"
      }
      env {
        name  = "TRADINGAGENTS_DATA_DIR"
        value = "/data"
      }
      env {
        name  = "TRADINGAGENTS_CACHE_DIR"
        value = "/data/cache"
      }
      env {
        name  = "AUTH_DISABLED"
        value = "true"
      }
      env {
        name  = "TRADINGAGENTS_API_RATE_LIMIT"
        value = "30/minute"
      }
    }

    scaling {
      min_instance_count = 0
      max_instance_count = 2 # stay below async-workload pressure
    }
  }

  traffic {
    percent = 100
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
  }

  depends_on = [
    google_project_service.apis["run.googleapis.com"],
  ]
}

# Allow public unauthenticated access (TradingAgents dashboard is public)
resource "google_cloud_run_service_iam_member" "public_access" {
  location = google_cloud_run_v2_service.main.location
  project  = var.project_id
  service  = google_cloud_run_v2_service.main.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Workload Identity Federation for GitHub Actions
resource "google_iam_workload_identity_pool" "github" {
  workload_identity_pool_id = "github-pool"
  display_name              = "GitHub Actions pool"
  description               = "Workload Identity Pool for GitHub Actions"
}

resource "google_iam_workload_identity_pool_provider" "github" {
  workload_identity_pool_provider_id = "github-provider"
  display_name                       = "GitHub Actions provider"
  description                        = "OIDC provider for GitHub Actions"
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id

  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.actor"      = "assertion.actor"
    "attribute.repository" = "assertion.repository"
  }

  attribute_condition = "attribute.repository == \"ido1Shapira/TradingAgents\""
  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

# Deploy service account for GitHub Actions
resource "google_service_account" "deploy" {
  account_id   = "tradingagents-deploy"
  display_name = "TradingAgents GitHub Actions deploy account"
}

resource "google_project_iam_member" "deploy_cloud_run_developer" {
  project = var.project_id
  role    = "roles/run.developer"
  member  = "serviceAccount:${google_service_account.deploy.email}"
}

resource "google_project_iam_member" "deploy_log_viewer" {
  project = var.project_id
  role    = "roles/logging.viewer"
  member  = "serviceAccount:${google_service_account.deploy.email}"
}

resource "google_service_account_iam_member" "deploy_workload_identity_user" {
  service_account_id = google_service_account.deploy.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/${var.github_owner}/${var.github_repo}"
}

# Allow the deploy SA to act-as the Cloud Run SA when running
# ``gcloud run deploy`` (needs ``iam.serviceAccounts.actAs``).
resource "google_service_account_iam_member" "deploy_cloud_run_act_as" {
  service_account_id = google_service_account.cloud_run.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.deploy.email}"
}
