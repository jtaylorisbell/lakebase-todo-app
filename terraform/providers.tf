terraform {
  required_version = ">= 1.5"

  required_providers {
    databricks = {
      source  = "databricks/databricks"
      version = ">= 1.65.0"
    }
  }
}

provider "databricks" {
  # Reads DATABRICKS_HOST + cached OAuth automatically.
  # Or set: host, token, azure_workspace_resource_id, etc.
}
