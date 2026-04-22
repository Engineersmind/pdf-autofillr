##############################################################################
# modules/gcp/main.tf
# GCP mirror: Cloud Storage + Cloud Run + Secret Manager + Cloud Logging
##############################################################################

terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

# ── Cloud Storage: RAG bucket mirror ─────────────────────────────────────────

resource "google_storage_bucket" "rag" {
  name                        = "${var.name_prefix}-rag"
  location                    = upper(var.gcp_region)
  project                     = var.gcp_project_id
  uniform_bucket_level_access = true
  force_destroy               = var.environment != "prod"

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition { age = 90; matches_prefix = ["log/"] }
    action    { type = "Delete" }
  }

  lifecycle_rule {
    condition { age = 30; matches_prefix = ["vectors/"] }
    action    { type = "SetStorageClass"; storage_class = "NEARLINE" }
  }

  labels = {
    environment = var.environment
    service     = "rag-lambda"
  }
}

resource "google_storage_bucket" "prod" {
  name                        = "${var.name_prefix}-production"
  location                    = upper(var.gcp_region)
  project                     = var.gcp_project_id
  uniform_bucket_level_access = true
  force_destroy               = false

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition { age = 365; matches_prefix = ["shared/filled_pdf_store/"] }
    action    { type = "Delete" }
  }

  labels = {
    environment = var.environment
    service     = "rag-lambda"
    role        = "production-store"
  }
}

# ── Secret Manager ────────────────────────────────────────────────────────────

resource "google_secret_manager_secret" "openai_api_key" {
  secret_id = "${var.name_prefix}-openai-api-key"
  project   = var.gcp_project_id

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "openai_api_key" {
  secret      = google_secret_manager_secret.openai_api_key.id
  secret_data = var.openai_api_key
}

resource "google_secret_manager_secret" "x_api_key" {
  secret_id = "${var.name_prefix}-x-api-key"
  project   = var.gcp_project_id
  replication { auto {} }
}

resource "google_secret_manager_secret_version" "x_api_key" {
  secret      = google_secret_manager_secret.x_api_key.id
  secret_data = var.x_api_key
}

resource "google_secret_manager_secret" "teams_webhook_url" {
  secret_id = "${var.name_prefix}-teams-webhook"
  project   = var.gcp_project_id
  replication { auto {} }
}

resource "google_secret_manager_secret_version" "teams_webhook_url" {
  secret      = google_secret_manager_secret.teams_webhook_url.id
  secret_data = var.teams_webhook_url
}

# ── Artifact Registry (mirrors ECR) ──────────────────────────────────────────

resource "google_artifact_registry_repository" "rag" {
  repository_id = "${var.name_prefix}-repo"
  location      = var.gcp_region
  project       = var.gcp_project_id
  format        = "DOCKER"

  labels = {
    environment = var.environment
  }
}

# ── Service Account for Cloud Run ─────────────────────────────────────────────

resource "google_service_account" "rag_run" {
  account_id   = "${var.name_prefix}-run-sa"
  display_name = "RAG Lambda Cloud Run Service Account"
  project      = var.gcp_project_id
}

resource "google_project_iam_member" "rag_run_storage" {
  project = var.gcp_project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.rag_run.email}"
}

resource "google_project_iam_member" "rag_run_secrets" {
  project = var.gcp_project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.rag_run.email}"
}

# ── Log-based Metric for Errors ───────────────────────────────────────────────

resource "google_logging_metric" "rag_errors" {
  name    = "${var.name_prefix}-errors"
  project = var.gcp_project_id
  filter  = "resource.type=\"cloud_run_revision\" severity=ERROR"

  metric_descriptor {
    metric_kind = "DELTA"
    value_type  = "INT64"
    unit        = "1"
  }
}
