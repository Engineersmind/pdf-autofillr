##############################################################################
# modules/azure/outputs.tf
##############################################################################

output "storage_container_url" {
  value = "https://${azurerm_storage_account.rag.name}.blob.core.windows.net/${azurerm_storage_container.rag.name}"
}

output "key_vault_uri" {
  value = azurerm_key_vault.rag.vault_uri
}

output "acr_login_server" {
  value = azurerm_container_registry.rag.login_server
}

output "app_insights_instrumentation_key" {
  value     = azurerm_application_insights.rag.instrumentation_key
  sensitive = true
}
