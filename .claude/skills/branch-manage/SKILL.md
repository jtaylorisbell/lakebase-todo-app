---
name: branch-manage
description: Create, reset, delete, or list Lakebase dev branches.
trigger: User asks to create, reset, delete, or list dev branches, or mentions branch management.
---

# Branch Management

Manage Lakebase Postgres dev branches via Makefile targets wrapping the `databricks postgres` CLI.

## Operations

### Create a branch

```bash
make branch-create NAME=dev-{first-last}
```

After creation, run migrations on the new branch:

```bash
LAKEBASE_BRANCH_ID=dev-{first-last} uv run alembic upgrade head
```

Remind the user to **enable Data API** on the new branch's endpoint via Lakebase UI before using PostgREST.

### Reset a branch

Resets branch data back to the production fork point:

```bash
make branch-reset NAME=dev-{first-last}
```

After reset, re-run migrations:

```bash
LAKEBASE_BRANCH_ID=dev-{first-last} uv run alembic upgrade head
```

### Delete a branch

```bash
make branch-delete NAME=dev-{first-last}
```

Confirm with the user before deleting — this is irreversible.

### List branches

```bash
make branch-list
```

## Conventions

- Branch naming: `dev-{first-last}` derived from email prefix (e.g., `taylor.isbell@co.com` -> `dev-taylor-isbell`)
- The `production` branch is the default and should never be deleted or reset manually
- `LAKEBASE_BRANCH_ID` env var targets a specific branch for migrations and the backend server
- The `.env` file should have `DATABRICKS_CONFIG_PROFILE=todo-app-dev`
