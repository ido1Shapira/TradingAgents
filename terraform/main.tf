resource "google_project_service" "apis" {
  for_each = toset([
    "run.googleapis.com",
    "artifactregistry.googleapis.com",
    "iamcredentials.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "storage.googleapis.com",
    "secretmanager.googleapis.com",
  ])
  service            = each.key
  disable_on_destroy = false
}

# Artifact Registry for Docker images
resource "google_artifact_registry_repository" "main" {
  location      = var.region
  repository_id = "tradingagents-images"
  description   = "Docker images for TradingAgents"
  format        = "DOCKER"
  depends_on    = [google_project_service.apis["artifactregistry.googleapis.com"]]
}

# Cloud Storage bucket for persistent data (free tier: 5GB Standard)
resource "google_storage_bucket" "data" {
  name                     = "${var.gcs_bucket_name}-${var.project_id}"
  location                 = var.region
  force_destroy            = false
  storage_class            = "STANDARD"
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"

  versioning {
    enabled = true
  }

  # Auto-cleanup old files (free-tier keepers: 5GB max)
  lifecycle_rule {
    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }
    condition {
      age = 30
    }
  }

  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      age = 365
    }
  }

  depends_on = [google_project_service.apis["storage.googleapis.com"]]
}

# Cloud Run service account
resource "google_service_account" "cloud_run" {
  account_id   = "tradingagents-cloud-run"
  display_name = "TradingAgents Cloud Run service account"
}

resource "google_storage_bucket_iam_member" "cloud_run_storage" {
  bucket = google_storage_bucket.data.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.cloud_run.email}"
}

resource "google_project_iam_member" "cloud_run_secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.cloud_run.email}"
}

# Cloud Run service (single shared deployment; staging prefix removed to keep free)
resource "google_cloud_run_v2_service" "main" {
  name     = "tradingagents"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.cloud_run.email
    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/tradingagents-images/app:latest"
      ports {
        container_port = 8000
      }

      resources {
        limits = {
          memory = var.cloud_run_memory
          cpu    = var.cloud_run_cpu
        }
      }

      # Free-tier-friendly startup
      startup_probe {
        http_get {
          path = "/api/health"
          port = 8000
        }
        initial_delay_seconds = 5
        period_seconds        = 5
        failure_threshold     = 12
      }
      liveness_probe {
        http_get {
          path = "/api/health"
          port = 8000
        }
        period_seconds    = 30
        failure_threshold = 3
      }

      env {
        name  = "PORT"
        value = "8000"
      }
      env {
        name  = "TRADINGAGENTS_DASHBOARD_HOST"
        value = "0.0.0.0"
      }
      env {
        name  = "GCS_BUCKET"
        value = google_storage_bucket.data.name
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
      max_instance_count = 2  # stay below async-workload pressure
    }
  }

  traffic {
    percent = 100
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
  }

  depends_on = [
    google_project_service.apis["run.googleapis.com"],
    google_artifact_registry_repository.main,
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

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

# Deploy service account for GitHub Actions
resource "google_service_account" "deploy" {
  account_id   = "tradingagents-deploy"
  display_name = "TradingAgents GitHub Actions deploy account"
}

resource "google_project_iam_member" "deploy_artifact_registry_writer" {
  project = var.project_id
  role    = "roles/artifactregistry.writer"
  member  = "serviceAccount:${google_service_account.deploy.email}"
}

resource "google_project_iam_member" "deploy_cloud_run_developer" {
  project = var.project_id
  role    = "roles/run.developer"
  member  = "serviceAccount:${google_service_account.deploy.email}"
}

resource "google_project_iam_member" "deploy_storage_admin" {
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.deploy.email}"
}

resource "google_service_account_iam_member" "deploy_workload_identity_user" {
  service_account_id = google_service_account.deploy.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/${var.github_owner}/${var.github_repo}"
}
