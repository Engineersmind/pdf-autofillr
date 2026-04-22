##############################################################################
# modules/azure/variables.tf
##############################################################################

variable "environment"           { type = string }
variable "azure_location"        { type = string }
variable "name_prefix"           { type = string }
variable "common_tags"           { type = map(string) }
variable "resource_group_name"   { type = string }

variable "openai_api_key"        { type = string; sensitive = true }
variable "x_api_key"             { type = string; sensitive = true }
variable "teams_webhook_url"     { type = string; sensitive = true }
