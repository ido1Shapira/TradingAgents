output "artifact_registry_repo" {
  value = google_artifact_registry_repository.main.id
}

output "cloud_sql_instance_name" {
  value = google_sql_database_instance.main.name
}

output "cloud_sql_public_ip" {
  value = google_sql_database_instance.main.public_ip_address
}

output "cloud_run_staging_url" {
  value = google_cloud_run_v2_service.staging.uri
}

output "cloud_run_production_url" {
  value = google_cloud_run_v2_service.production.uri
}

output "workload_identity_provider" {
  value = google_iam_workload_identity_pool_provider.github.name
}

output "deploy_service_account_email" {
  value = google_service_account.deploy.email
}

output "db_url_secret_id" {
  value = google_secret_manager_secret.db_url.secret_id
}

output "db_url_sync_secret_id" {
  value = google_secret_manager_secret.db_url_sync.secret_id
}
