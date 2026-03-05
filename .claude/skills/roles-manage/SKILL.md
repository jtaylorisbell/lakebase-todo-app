---
name: roles-manage
description: Manage Postgres roles, permissions, and Data API access via lbctl.
trigger: User asks about role management, Postgres permissions, Data API access, grants, lbctl, or database user provisioning.
---

# Role Management

Manage database-layer Postgres roles using `lbctl` (Typer CLI). Source of truth is `db/roles.yml`. Full CLI reference: `src/todo_app/cli/README.md`.

## Operations

### Show drift (diff)

Compare `db/roles.yml` against live Postgres — exits code 1 if drifted (CI-friendly):

```bash
uv run lbctl roles diff --config db/roles.yml
```

Or: `make roles-diff`

### Sync roles

Apply `db/roles.yml` to live Postgres — creates missing roles, upgrades/downgrades permissions, adds authenticator grants:

```bash
uv run lbctl roles sync --config db/roles.yml
```

With app service principal:
```bash
uv run lbctl roles sync --config db/roles.yml --app lakebase-todo-app-dev
```

Preview without applying:
```bash
uv run lbctl roles sync --config db/roles.yml --dry-run
```

Revoke roles not in config:
```bash
uv run lbctl roles sync --config db/roles.yml --revoke
```

Or: `make roles-sync`

### Add a user to config

Edit `db/roles.yml` — append under `users:`:

```yaml
users:
  - email: existing@databricks.com
    access: readwrite
  - email: NEW_EMAIL
    access: readwrite  # or readonly
```

Validate no duplicate emails. After editing, run `roles sync` or push to main for CI.

### Ad-hoc provisioning

One-off grants without editing config:

```bash
# Developer (read-write)
uv run lbctl roles provision --engineers dev@co.com

# Read-only
uv run lbctl roles provision --readonly analyst@co.com

# App service principal
uv run lbctl roles provision --app lakebase-todo-app-dev
```

## What each role gets

- `CONNECT` on `databricks_postgres`
- `USAGE` (+ `CREATE` for readwrite) on `public` schema
- `SELECT, INSERT, UPDATE, DELETE` on all tables (readwrite) or `SELECT` only (readonly)
- `USAGE, SELECT` on all sequences
- `ALTER DEFAULT PRIVILEGES` for future objects
- `GRANT TO authenticator` for Data API access
