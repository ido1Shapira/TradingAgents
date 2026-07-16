variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "us-central1"
}

variable "github_owner" {
  description = "GitHub repository owner"
  type        = string
}

variable "github_repo" {
  description = "GitHub repository name"
  type        = string
  default     = "TradingAgents"
}

variable "gcs_bucket_name" {
  description = "Name of the GCS bucket; must be globally unique. Stays within free tier (5GB Standard)."
  type        = string
  default     = "tradingagent-data-files"
}

variable "cloud_run_memory" {
  description = "Cloud Run memory in MiB (free tier covers this up to 4GB-seconds/request)"
  type        = string
  default     = "512Mi"
}

variable "cloud_run_cpu" {
  description = "Cloud Run vCPU (1 vCPU = 1000m)"
  type        = string
  default     = "1000m"
}
