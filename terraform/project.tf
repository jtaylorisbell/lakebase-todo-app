# ── Lakebase project ────────────────────────────
# Creating the project automatically provisions:
#   • a "production" branch (the root / default branch)
#   • a read-write endpoint on that branch

resource "databricks_postgres_project" "this" {
  project_id = var.project_id

  spec = {
    display_name = var.project_display_name
    pg_version   = var.pg_version
  }
}
