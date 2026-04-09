terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }
}

provider "azurerm" {
  features {}
}

variable "env"          { default = "dev" }
variable "location"     { default = "East US" }
variable "image_uri"    { description = "ACR image URI" }
variable "llm_model"    { default = "gpt-4o" }
variable "rag_api_url"  { default = "" }

locals {
  name = "pdf-autofillr-mapper-${var.env}"
  tags = { Project = "pdf-autofillr", Module = "mapper", Env = var.env }
}

resource "azurerm_resource_group" "mapper" {
  name     = local.name
  location = var.location
  tags     = local.tags
}

resource "azurerm_container_app_environment" "mapper" {
  name                = "${local.name}-env"
  location            = azurerm_resource_group.mapper.location
  resource_group_name = azurerm_resource_group.mapper.name
  tags                = local.tags
}

resource "azurerm_container_app" "mapper" {
  name                         = local.name
  container_app_environment_id = azurerm_container_app_environment.mapper.id
  resource_group_name          = azurerm_resource_group.mapper.name
  revision_mode                = "Single"
  tags                         = local.tags

  template {
    container {
      name   = "mapper"
      image  = var.image_uri
      cpu    = 2.0
      memory = "4Gi"

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
    }
  }

  ingress {
    external_enabled = true
    target_port      = 8000
    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }
}

output "app_url" {
  value = "https://${azurerm_container_app.mapper.ingress[0].fqdn}"
}
