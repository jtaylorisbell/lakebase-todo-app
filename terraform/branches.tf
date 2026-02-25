# ── Additional long-lived branches ───────────────
# Each branch gets its own read-write endpoint for
# independent development / staging work.

resource "databricks_postgres_branch" "extra" {
  for_each = var.extra_branches

  parent    = databricks_postgres_project.this.name # parent = production
  branch_id = each.key

  spec = {
    no_expiry = each.value.no_expiry
  }
}

resource "databricks_postgres_endpoint" "extra" {
  for_each = var.extra_branches

  parent      = databricks_postgres_branch.extra[each.key].name
  endpoint_id = "primary"

  spec = {
    endpoint_type            = "ENDPOINT_TYPE_READ_WRITE"
    autoscaling_limit_min_cu = each.value.min_cu
    autoscaling_limit_max_cu = each.value.max_cu
  }
}
