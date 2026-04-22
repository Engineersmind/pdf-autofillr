terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

variable "env"         { default = "dev" }
variable "project_id"  { description = "GCP project ID" }
variable "region"      { default = "us-central1" }
variable "image_uri"   { description = "Artifact Registry image URI" }
variable "llm_model"   { default = "gpt-4o" }
variable "rag_api_url" { default = "" }

provider "google" {
  project = var.project_id
  region  = var.region
}

locals {
  name = "pdf-autofillr-mapper-${var.env}"
}

resource "google_cloud_run_v2_service" "mapper" {
  name     = local.name
  location = var.region

  template {
    containers {
      image = var.image_uri

      resources {
        limits = { cpu = "2", memory = "4Gi" }
      }

      env {
        name  = "DEPLOY_MODE"
        value = "fastapi"
      }
      env {
        name  = "LLM_MODEL"
        value = var.llm_model
      }
      env {
        name  = "RAG_API_URL"
        value = var.rag_api_url
      }

      ports {
        container_port = 8000
      }
    }
  }

  labels = { env = var.env, module = "mapper" }
}

# Allow unauthenticated access (remove for private deployments)
resource "google_cloud_run_service_iam_member" "public" {
  location = google_cloud_run_v2_service.mapper.location
  service  = google_cloud_run_v2_service.mapper.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

output "service_url" {
  value = google_cloud_run_v2_service.mapper.uri
}
