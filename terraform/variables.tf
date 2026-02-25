# ── Project ──────────────────────────────────────
variable "project_id" {
  description = "Immutable resource ID for the Lakebase project (lowercase, hyphens, 1-63 chars)."
  type        = string
  default     = "my-app"
}

variable "project_display_name" {
  description = "Human-readable display name shown in the Lakebase App."
  type        = string
  default     = "My Application"
}

variable "pg_version" {
  description = "Postgres major version."
  type        = number
  default     = 17
}

# ── Branches ─────────────────────────────────────
variable "extra_branches" {
  description = "Map of additional long-lived branches to create beneath the default production branch."
  type = map(object({
    min_cu    = number
    max_cu    = number
    no_expiry = bool
  }))
  default = {
    development = { min_cu = 0.5, max_cu = 2, no_expiry = true }
    staging     = { min_cu = 0.5, max_cu = 4, no_expiry = true }
  }
}

# ── Permissions ──────────────────────────────────
variable "manage_users" {
  description = "List of Databricks user emails to grant CAN_MANAGE on the project."
  type        = list(string)
  default     = []
}

variable "use_users" {
  description = "List of Databricks user emails to grant CAN_USE on the project."
  type        = list(string)
  default     = []
}

variable "manage_groups" {
  description = "List of Databricks group names to grant CAN_MANAGE on the project."
  type        = list(string)
  default     = []
}

variable "use_groups" {
  description = "List of Databricks group names to grant CAN_USE on the project."
  type        = list(string)
  default     = []
}
