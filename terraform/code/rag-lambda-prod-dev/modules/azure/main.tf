##############################################################################
# modules/azure/main.tf
# Azure mirror: Blob Storage + Azure Functions container + Key Vault
##############################################################################

terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }
}

# ── Resource Group ────────────────────────────────────────────────────────────

resource "azurerm_resource_group" "rag" {
  name     = var.resource_group_name
  location = var.azure_location
  tags     = var.common_tags
}

# ── Storage Account (mirrors rag-bucket-pdf-filler) ───────────────────────────

resource "azurerm_storage_account" "rag" {
  name                     = replace("${var.name_prefix}rag", "-", "")
  resource_group_name      = azurerm_resource_group.rag.name
  location                 = azurerm_resource_group.rag.location
  account_tier             = "Standard"
  account_replication_type = "LRS"

  blob_properties {
    versioning_enabled = true
    delete_retention_policy {
      days = 14
    }
  }

  tags = var.common_tags
}

resource "azurerm_storage_container" "rag" {
  name                  = "rag-bucket"
  storage_account_name  = azurerm_storage_account.rag.name
  container_access_type = "private"
}

resource "azurerm_storage_container" "prod" {
  name                  = "pdf-fillr-production"
  storage_account_name  = azurerm_storage_account.rag.name
  container_access_type = "private"
}

# ── Key Vault (replaces Secrets Manager) ─────────────────────────────────────

resource "azurerm_key_vault" "rag" {
  name                = "${var.name_prefix}-kv"
  location            = azurerm_resource_group.rag.location
  resource_group_name = azurerm_resource_group.rag.name
  tenant_id           = data.azurerm_client_config.current.tenant_id
  sku_name            = "standard"

  soft_delete_retention_days = var.environment == "prod" ? 30 : 7
  purge_protection_enabled   = var.environment == "prod"

  tags = var.common_tags
}

data "azurerm_client_config" "current" {}

resource "azurerm_key_vault_access_policy" "terraform" {
  key_vault_id = azurerm_key_vault.rag.id
  tenant_id    = data.azurerm_client_config.current.tenant_id
  object_id    = data.azurerm_client_config.current.object_id

  secret_permissions = ["Get", "List", "Set", "Delete", "Purge"]
}

resource "azurerm_key_vault_secret" "openai_api_key" {
  name         = "OPENAI-API-KEY"
  value        = var.openai_api_key
  key_vault_id = azurerm_key_vault.rag.id
  depends_on   = [azurerm_key_vault_access_policy.terraform]
}

resource "azurerm_key_vault_secret" "x_api_key" {
  name         = "X-API-KEY"
  value        = var.x_api_key
  key_vault_id = azurerm_key_vault.rag.id
  depends_on   = [azurerm_key_vault_access_policy.terraform]
}

resource "azurerm_key_vault_secret" "teams_webhook_url" {
  name         = "TEAMS-WEBHOOK-URL"
  value        = var.teams_webhook_url
  key_vault_id = azurerm_key_vault.rag.id
  depends_on   = [azurerm_key_vault_access_policy.terraform]
}

# ── Azure Container Registry ──────────────────────────────────────────────────

resource "azurerm_container_registry" "rag" {
  name                = replace("${var.name_prefix}acr", "-", "")
  resource_group_name = azurerm_resource_group.rag.name
  location            = azurerm_resource_group.rag.location
  sku                 = "Basic"
  admin_enabled       = true
  tags                = var.common_tags
}

# ── Azure Function App (container-based, mirrors AWS Lambda) ──────────────────

resource "azurerm_service_plan" "rag" {
  name                = "${var.name_prefix}-plan"
  resource_group_name = azurerm_resource_group.rag.name
  location            = azurerm_resource_group.rag.location
  os_type             = "Linux"
  sku_name            = "Y1"   # Consumption plan (serverless)
  tags                = var.common_tags
}

resource "azurerm_storage_account" "functions" {
  name                     = replace("${var.name_prefix}fn", "-", "")
  resource_group_name      = azurerm_resource_group.rag.name
  location                 = azurerm_resource_group.rag.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  tags                     = var.common_tags
}

# ── Log Analytics + App Insights ─────────────────────────────────────────────

resource "azurerm_log_analytics_workspace" "rag" {
  name                = "${var.name_prefix}-logs"
  location            = azurerm_resource_group.rag.location
  resource_group_name = azurerm_resource_group.rag.name
  sku                 = "PerGB2018"
  retention_in_days   = var.environment == "prod" ? 90 : 14
  tags                = var.common_tags
}

resource "azurerm_application_insights" "rag" {
  name                = "${var.name_prefix}-appinsights"
  location            = azurerm_resource_group.rag.location
  resource_group_name = azurerm_resource_group.rag.name
  workspace_id        = azurerm_log_analytics_workspace.rag.id
  application_type    = "web"
  tags                = var.common_tags
}
