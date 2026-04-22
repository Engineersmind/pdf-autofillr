##############################################################################
# modules/gcp/main.tf
# GCP mirror: 3 Cloud Storage buckets + Secret Manager + Artifact Registry
##############################################################################

terraform {
  required_providers {
    google = { source = "hashicorp/google"; version = "~> 5.0" }
  }
}

# ── Cloud Storage: static_bucket mirror ──────────────────────────────────────

resource "google_storage_bucket" "static" {
  name                        = "${var.name_prefix}-static"
  location                    = upper(var.gcp_region)
  project                     = var.gcp_project_id
  uniform_bucket_level_access = true
  force_destroy               = var.environment != "prod"

  versioning { enabled = true }

  lifecycle_rule {
    condition { age = 90; matches_prefix = ["outputs/"] }
    action    { type = "Delete" }
  }

  labels = { environment = var.environment; service = "doc-upload" }
}

# ── Cloud Storage: output_bucket mirror ──────────────────────────────────────

resource "google_storage_bucket" "output" {
  name                        = "${var.name_prefix}-output"
  location                    = upper(var.gcp_region)
  project                     = var.gcp_project_id
  uniform_bucket_level_access = true
  force_destroy               = var.environment != "prod"

  versioning { enabled = true }

  lifecycle_rule {
    condition { age = 90 }
    action    { type = "Delete" }
  }

  labels = { environment = var.environment; role = "flat-json-handoff" }
}

# ── Cloud Storage: prod_bucket mirror ────────────────────────────────────────

resource "google_storage_bucket" "prod" {
  name                        = "${var.name_prefix}-production"
  location                    = upper(var.gcp_region)
  project                     = var.gcp_project_id
  uniform_bucket_level_access = true
  force_destroy               = false

  versioning { enabled = true }

  lifecycle_rule {
    condition { age = 365; matches_prefix = ["prod/"] }
    action    { type = "Delete" }
  }
  lifecycle_rule {
    condition { age = 90; matches_prefix = ["dev/"] }
    action    { type = "Delete" }
  }
  lifecycle_rule {
    condition { age = 30; matches_prefix = ["local/"] }
    action    { type = "Delete" }
  }

  labels = { environment = var.environment; role = "dual-write-mirror" }
}

# ── Secret Manager — all 4 sensitive vars ────────────────────────────────────

locals {
  secrets = {
    auth-token        = var.auth_token
    openai-api-key    = var.openai_api_key
    pdf-api-key       = var.pdf_api_key
    teams-webhook-url = var.teams_webhook_url
  }
}

resource "google_secret_manager_secret" "extractor" {
  for_each  = local.secrets
  secret_id = "${var.name_prefix}-${each.key}"
  project   = var.gcp_project_id
  replication { auto {} }
}

resource "google_secret_manager_secret_version" "extractor" {
  for_each    = local.secrets
  secret      = google_secret_manager_secret.extractor[each.key].id
  secret_data = each.value
}

# ── Artifact Registry ────────────────────────────────────────────────────────

resource "google_artifact_registry_repository" "extractor" {
  repository_id = "${var.name_prefix}-repo"
  location      = var.gcp_region
  project       = var.gcp_project_id
  format        = "DOCKER"
  labels        = { environment = var.environment }
}

# ── Service Account ───────────────────────────────────────────────────────────

resource "google_service_account" "extractor" {
  account_id   = "${var.name_prefix}-sa"
  display_name = "PDF Extractor Service Account"
  project      = var.gcp_project_id
}

resource "google_project_iam_member" "storage_admin" {
  project = var.gcp_project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.extractor.email}"
}

resource "google_project_iam_member" "secrets_accessor" {
  project = var.gcp_project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.extractor.email}"
}

##############################################################################
# modules/gcp/variables.tf
##############################################################################

variable "environment"       { type = string }
variable "gcp_project_id"    { type = string }
variable "gcp_region"        { type = string }
variable "name_prefix"       { type = string }
variable "auth_token"        { type = string; sensitive = true }
variable "openai_api_key"    { type = string; sensitive = true }
variable "pdf_api_key"       { type = string; sensitive = true }
variable "teams_webhook_url" { type = string; sensitive = true }

##############################################################################
# modules/gcp/outputs.tf
##############################################################################

output "storage_bucket_url"        { value = "gs://${google_storage_bucket.static.name}" }
output "output_bucket_url"         { value = "gs://${google_storage_bucket.output.name}" }
output "prod_bucket_url"           { value = "gs://${google_storage_bucket.prod.name}" }
output "artifact_registry_url"     { value = "${var.gcp_region}-docker.pkg.dev/${var.gcp_project_id}/${google_artifact_registry_repository.extractor.repository_id}" }
output "service_account_email"     { value = google_service_account.extractor.email }
