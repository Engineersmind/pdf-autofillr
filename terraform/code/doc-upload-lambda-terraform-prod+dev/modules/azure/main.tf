##############################################################################
# modules/azure/main.tf
# Azure mirror: 3 Blob containers (static/output/prod) + Key Vault + ACR
##############################################################################

terraform {
  required_providers {
    azurerm = { source = "hashicorp/azurerm"; version = "~> 3.0" }
  }
}

resource "azurerm_resource_group" "extractor" {
  name     = var.resource_group_name
  location = var.azure_location
  tags     = var.common_tags
}

# ── Storage Account — mirrors all 3 S3 buckets ────────────────────────────────

resource "azurerm_storage_account" "extractor" {
  name                     = replace(substr("${var.name_prefix}sa", 0, 24), "-", "")
  resource_group_name      = azurerm_resource_group.extractor.name
  location                 = azurerm_resource_group.extractor.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  blob_properties {
    versioning_enabled = true
    delete_retention_policy { days = 14 }
  }
  tags = var.common_tags
}

# static_bucket mirror: schema + per-session outputs + logs
resource "azurerm_storage_container" "static" {
  name                  = "pdf-filler-static"
  storage_account_name  = azurerm_storage_account.extractor.name
  container_access_type = "private"
}

# output_bucket mirror: flat JSON handoff
resource "azurerm_storage_container" "output" {
  name                  = "chatbot-outputs"
  storage_account_name  = azurerm_storage_account.extractor.name
  container_access_type = "private"
}

# prod_bucket mirror: dual-write
resource "azurerm_storage_container" "prod" {
  name                  = "pdf-fillr-production"
  storage_account_name  = azurerm_storage_account.extractor.name
  container_access_type = "private"
}

# ── Key Vault — all 6 secrets from .env ──────────────────────────────────────

resource "azurerm_key_vault" "extractor" {
  name                       = "${var.name_prefix}-kv"
  location                   = azurerm_resource_group.extractor.location
  resource_group_name        = azurerm_resource_group.extractor.name
  tenant_id                  = data.azurerm_client_config.current.tenant_id
  sku_name                   = "standard"
  soft_delete_retention_days = var.environment == "prod" ? 30 : 7
  purge_protection_enabled   = var.environment == "prod"
  tags                       = var.common_tags
}

data "azurerm_client_config" "current" {}

resource "azurerm_key_vault_access_policy" "terraform" {
  key_vault_id = azurerm_key_vault.extractor.id
  tenant_id    = data.azurerm_client_config.current.tenant_id
  object_id    = data.azurerm_client_config.current.object_id
  secret_permissions = ["Get", "List", "Set", "Delete", "Purge"]
}

resource "azurerm_key_vault_secret" "auth_token" {
  name         = "AUTH-TOKEN"
  value        = var.auth_token
  key_vault_id = azurerm_key_vault.extractor.id
  depends_on   = [azurerm_key_vault_access_policy.terraform]
}

resource "azurerm_key_vault_secret" "openai_api_key" {
  name         = "OPENAI-API-KEY"
  value        = var.openai_api_key
  key_vault_id = azurerm_key_vault.extractor.id
  depends_on   = [azurerm_key_vault_access_policy.terraform]
}

resource "azurerm_key_vault_secret" "pdf_api_key" {
  name         = "PDF-API-KEY"
  value        = var.pdf_api_key
  key_vault_id = azurerm_key_vault.extractor.id
  depends_on   = [azurerm_key_vault_access_policy.terraform]
}

resource "azurerm_key_vault_secret" "teams_webhook_url" {
  name         = "TEAMS-WEBHOOK-URL"
  value        = var.teams_webhook_url
  key_vault_id = azurerm_key_vault.extractor.id
  depends_on   = [azurerm_key_vault_access_policy.terraform]
}

# ── ACR ───────────────────────────────────────────────────────────────────────

resource "azurerm_container_registry" "extractor" {
  name                = replace(substr("${var.name_prefix}acr", 0, 50), "-", "")
  resource_group_name = azurerm_resource_group.extractor.name
  location            = azurerm_resource_group.extractor.location
  sku                 = "Basic"
  admin_enabled       = true
  tags                = var.common_tags
}

# ── Log Analytics + App Insights ─────────────────────────────────────────────

resource "azurerm_log_analytics_workspace" "extractor" {
  name                = "${var.name_prefix}-logs"
  location            = azurerm_resource_group.extractor.location
  resource_group_name = azurerm_resource_group.extractor.name
  sku                 = "PerGB2018"
  retention_in_days   = var.environment == "prod" ? 90 : 14
  tags                = var.common_tags
}

resource "azurerm_application_insights" "extractor" {
  name                = "${var.name_prefix}-ai"
  location            = azurerm_resource_group.extractor.location
  resource_group_name = azurerm_resource_group.extractor.name
  workspace_id        = azurerm_log_analytics_workspace.extractor.id
  application_type    = "web"
  tags                = var.common_tags
}

##############################################################################
# modules/azure/variables.tf
##############################################################################

variable "environment"           { type = string }
variable "azure_location"        { type = string }
variable "name_prefix"           { type = string }
variable "common_tags"           { type = map(string) }
variable "resource_group_name"   { type = string }
variable "auth_token"            { type = string; sensitive = true }
variable "openai_api_key"        { type = string; sensitive = true }
variable "pdf_api_key"           { type = string; sensitive = true }
variable "teams_webhook_url"     { type = string; sensitive = true }

##############################################################################
# modules/azure/outputs.tf
##############################################################################

output "storage_container_url" {
  value = "https://${azurerm_storage_account.extractor.name}.blob.core.windows.net/${azurerm_storage_container.static.name}"
}
output "key_vault_uri"          { value = azurerm_key_vault.extractor.vault_uri }
output "acr_login_server"       { value = azurerm_container_registry.extractor.login_server }
output "app_insights_key" {
  value     = azurerm_application_insights.extractor.instrumentation_key
  sensitive = true
}
