# ── Project-level ACLs ──────────────────────────
# CAN_MANAGE → create/delete branches, manage computes, manage roles
# CAN_USE    → view resources, get connection URI, limited branch ops
#
# NOTE: This controls *platform* permissions only.
# Postgres database-level permissions (GRANT/REVOKE) are managed
# separately via scripts/manage_roles.py.

resource "databricks_permissions" "project" {
  database_project_name = databricks_postgres_project.this.project_id

  # ── CAN_MANAGE for individual users ────────────
  dynamic "access_control" {
    for_each = var.manage_users
    content {
      user_name        = access_control.value
      permission_level = "CAN_MANAGE"
    }
  }

  # ── CAN_USE for individual users ───────────────
  dynamic "access_control" {
    for_each = var.use_users
    content {
      user_name        = access_control.value
      permission_level = "CAN_USE"
    }
  }

  # ── CAN_MANAGE for groups ──────────────────────
  dynamic "access_control" {
    for_each = var.manage_groups
    content {
      group_name       = access_control.value
      permission_level = "CAN_MANAGE"
    }
  }

  # ── CAN_USE for groups ─────────────────────────
  dynamic "access_control" {
    for_each = var.use_groups
    content {
      group_name       = access_control.value
      permission_level = "CAN_USE"
    }
  }
}
