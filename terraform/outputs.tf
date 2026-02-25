output "project_name" {
  description = "Full resource name of the Lakebase project."
  value       = databricks_postgres_project.this.id
}

output "branch_ids" {
  description = "Map of branch key → full resource name."
  value = {
    for k, b in databricks_postgres_branch.extra : k => b.id
  }
}

output "endpoint_ids" {
  description = "Map of branch key → endpoint resource name."
  value = {
    for k, e in databricks_postgres_endpoint.extra : k => e.id
  }
}
