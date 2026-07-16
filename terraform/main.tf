provider "google" {
  project = var.project_id
  region  = var.region
}

# Enable required APIs
resource "google_project_service" "apis" {
  for_each = toset([
    "run.googleapis.com",
    "sqladmin.googleapis.com",
    "secretmanager.googleapis.com",
    "artifactregistry.googleapis.com",
    "iamcredentials.googleapis.com",
    "cloudresourcemanager.googleapis.com",
  ])
  service            = each.key
  disable_on_destroy = false
}

# Artifact Registry
resource "google_artifact_registry_repository" "main" {
  location      = var.region
  repository_id = "tradingagents-images"
  description   = "Docker images for TradingAgents"
  format        = "DOCKER"
  depends_on    = [google_project_service.apis["artifactregistry.googleapis.com"]]
}

# Random suffix for Cloud SQL instance name
resource "random_id" "db_suffix" {
  byte_length = 4
}

# Cloud SQL Postgres
resource "google_sql_database_instance" "main" {
  name             = "tradingagents-db-${random_id.db_suffix.hex}"
  database_version = "POSTGRES_16"
  region           = var.region

  settings {
    tier              = var.db_tier
    disk_size         = 10
    disk_type         = "PD_SSD"
    disk_autoresize   = true
    availability_type = "ZONALLY_AVAILABLE"

    ip_configuration {
      authorized_networks {
        name  = "allow-cloud-run"
        value = "0.0.0.0/0"
      }
    }

    backup_configuration {
      enabled                        = true
      point_in_time_recovery_enabled = true
      start_time                     = "03:00"
    }
  }

  deletion_protection = false

  depends_on = [google_project_service.apis["sqladmin.googleapis.com"]]
}

resource "google_sql_database" "main" {
  name     = var.db_name
  instance = google_sql_database_instance.main.name
}

resource "random_password" "db_password" {
  length  = 24
  special = false
}

resource "google_sql_user" "app" {
  name     = var.db_user
  instance = google_sql_database_instance.main.name
  password = random_password.db_password.result
}

# Secret Manager — database URL
resource "google_secret_manager_secret" "db_url" {
  secret_id = "tradingagents-database-url"
  replication {
    auto {}
  }
  depends_on = [google_project_service.apis["secretmanager.googleapis.com"]]
}

resource "google_secret_manager_secret_version" "db_url" {
  secret      = google_secret_manager_secret.db_url.id
  secret_data = "postgresql+asyncpg://${google_sql_user.app.name}:${urlencode(random_password.db_password.result)}@${google_sql_database_instance.main.public_ip_address}/${google_sql_database.main.name}"
}

resource "google_secret_manager_secret" "db_url_sync" {
  secret_id = "tradingagents-database-url-sync"
  replication {
    auto {}
  }
  depends_on = [google_project_service.apis["secretmanager.googleapis.com"]]
}

resource "google_secret_manager_secret_version" "db_url_sync" {
  secret      = google_secret_manager_secret.db_url_sync.id
  secret_data = "postgresql+psycopg2://${google_sql_user.app.name}:${urlencode(random_password.db_password.result)}@${google_sql_database_instance.main.public_ip_address}/${google_sql_database.main.name}"
}

# Secret Manager — Upstash Redis
resource "google_secret_manager_secret" "upstash_url" {
  secret_id = "tradingagents-upstash-redis-url"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret" "upstash_token" {
  secret_id = "tradingagents-upstash-redis-token"
  replication {
    auto {}
  }
}

# Cloud Run service account
resource "google_service_account" "cloud_run" {
  account_id   = "tradingagents-cloud-run"
  display_name = "TradingAgents Cloud Run service account"
}

resource "google_project_iam_member" "cloud_run_sql_client" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.cloud_run.email}"
}

resource "google_project_iam_member" "cloud_run_secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.cloud_run.email}"
}

# Cloud Run services
resource "google_cloud_run_v2_service" "staging" {
  name     = "tradingagents-staging"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.cloud_run.email
    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/tradingagents-images/app:latest"
      ports {
        container_port = 8000
      }
      env {
        name  = "PORT"
        value = "8000"
      }
      env {
        name = "DATABASE_URL"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.db_url.secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "UPSTASH_REDIS_URL"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.upstash_url.secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "UPSTASH_REDIS_TOKEN"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.upstash_token.secret_id
            version = "latest"
          }
        }
      }
      env {
        name  = "AUTH_DISABLED"
        value = "true"
      }
    }
  }

  depends_on = [
    google_project_service.apis["run.googleapis.com"],
    google_artifact_registry_repository.main,
  ]
}

resource "google_cloud_run_v2_service" "production" {
  name     = "tradingagents-production"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.cloud_run.email
    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/tradingagents-images/app:latest"
      ports {
        container_port = 8000
      }
      env {
        name  = "PORT"
        value = "8000"
      }
      env {
        name = "DATABASE_URL"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.db_url.secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "UPSTASH_REDIS_URL"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.upstash_url.secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "UPSTASH_REDIS_TOKEN"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.upstash_token.secret_id
            version = "latest"
          }
        }
      }
    }
  }

  depends_on = [
    google_project_service.apis["run.googleapis.com"],
    google_artifact_registry_repository.main,
  ]
}

# Cloud Run Job for migrations
resource "google_cloud_run_v2_job" "migrate" {
  name     = "tradingagents-migrate"
  location = var.region

  template {
    task_count = 1
    template {
      service_account = google_service_account.cloud_run.email
      containers {
        image   = "${var.region}-docker.pkg.dev/${var.project_id}/tradingagents-images/app:latest"
        command = ["alembic", "upgrade", "head"]
        env {
          name = "DATABASE_URL"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.db_url_sync.secret_id
              version = "latest"
            }
          }
        }
      }
    }
  }

  depends_on = [google_project_service.apis["run.googleapis.com"]]
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

resource "google_project_iam_member" "deploy_cloud_run_invoker" {
  project = var.project_id
  role    = "roles/run.invoker"
  member  = "serviceAccount:${google_service_account.deploy.email}"
}

resource "google_project_iam_member" "deploy_secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.deploy.email}"
}

resource "google_project_iam_member" "deploy_sql_client" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.deploy.email}"
}

resource "google_service_account_iam_member" "deploy_workload_identity_user" {
  service_account_id = google_service_account.deploy.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/${var.github_owner}/${var.github_repo}"
}
