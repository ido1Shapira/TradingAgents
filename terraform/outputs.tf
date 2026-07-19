output "artifact_registry_repo" {
  value = google_artifact_registry_repository.main.id
}

output "cloud_run_url" {
  value = google_cloud_run_v2_service.main.uri
}

output "workload_identity_provider" {
  value = google_iam_workload_identity_pool_provider.github.name
}

output "deploy_service_account_email" {
  value = google_service_account.deploy.email
}
