##############################################################################
# modules/gcp/variables.tf
##############################################################################

variable "environment"      { type = string }
variable "gcp_project_id"   { type = string }
variable "gcp_region"       { type = string }
variable "name_prefix"      { type = string }

variable "openai_api_key"   { type = string; sensitive = true }
variable "x_api_key"        { type = string; sensitive = true }
variable "teams_webhook_url" { type = string; sensitive = true }

##############################################################################
# modules/gcp/outputs.tf
##############################################################################

output "storage_bucket_url" {
  value = "gs://${google_storage_bucket.rag.name}"
}

output "prod_bucket_url" {
  value = "gs://${google_storage_bucket.prod.name}"
}

output "artifact_registry_url" {
  value = "${var.gcp_region}-docker.pkg.dev/${var.gcp_project_id}/${google_artifact_registry_repository.rag.repository_id}"
}

output "run_service_account_email" {
  value = google_service_account.rag_run.email
}
