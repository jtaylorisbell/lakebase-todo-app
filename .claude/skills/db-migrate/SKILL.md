---
name: db-migrate
description: Run, create, check status, or rollback Alembic database migrations.
trigger: User asks about migrations, schema changes, alembic, or database schema.
---

# Database Migrations

Alembic migrations targeting a Lakebase Postgres branch. The `LAKEBASE_BRANCH_ID` env var controls which branch is targeted. If unset, auto-detection derives it from the authenticated user's email (`dev-{first-last}`).

## Operations

### Run pending migrations

```bash
LAKEBASE_BRANCH_ID={branch} uv run alembic upgrade head
```

For the production branch:
```bash
LAKEBASE_BRANCH_ID=production uv run alembic upgrade head
```

Or use the Makefile shortcut (uses `BRANCH` from `.env` or defaults to `production`):
```bash
make migrate
```

### Check migration status

```bash
LAKEBASE_BRANCH_ID={branch} uv run alembic current
```

Or: `make migrate-status`

### Create a new migration

Without autogenerate (empty template):
```bash
uv run alembic revision -m "description of change"
```

With autogenerate (compares models to DB — needs a running branch):
```bash
LAKEBASE_BRANCH_ID={branch} uv run alembic revision --autogenerate -m "description of change"
```

Migration files are created in `alembic/versions/`.

### Downgrade (rollback last migration)

```bash
LAKEBASE_BRANCH_ID={branch} uv run alembic downgrade -1
```

Or: `make migrate-downgrade`

## Key Details

- `alembic/env.py` resolves DB credentials dynamically via Databricks SDK OAuth
- Always specify `LAKEBASE_BRANCH_ID` when targeting a non-default branch
- Autogenerate requires a live DB connection, so set the branch target
- Migration dependency chain is in the `revision` and `down_revision` fields of each migration file
