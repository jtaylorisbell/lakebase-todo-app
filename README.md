# Lakebase Todo App

A full-stack To-Do list application powered by [Databricks Apps](https://docs.databricks.com/dev-tools/databricks-apps/) and [Lakebase](https://docs.databricks.com/en/lakebase/) (managed PostgreSQL).

**Backend:** FastAPI + psycopg + Databricks SDK OAuth
**Frontend:** React 19 + TypeScript + Tailwind CSS v4 + TanStack Query
**Database:** Lakebase Autoscaling (PostgreSQL)
**Deployment:** Databricks Asset Bundles (DAB)

## Project Structure

```
lakebase-todo-app/
├── app.py                  # Uvicorn entry point (adds src/ to path)
├── app.yaml                # Databricks Apps runtime config
├── databricks.yml          # DAB bundle configuration
├── pyproject.toml          # Python project + dependencies (uv)
├── requirements.txt        # Pinned deps for Databricks Apps runtime
├── alembic.ini             # Alembic migration config
├── alembic/
│   ├── env.py              # Migration environment (OAuth-aware)
│   ├── script.py.mako      # Migration file template
│   └── versions/           # Migration scripts
├── resources/
│   └── todo_app.yml        # DAB app resource definition
├── src/todo_app/
│   ├── __init__.py
│   ├── config.py           # Settings + OAuth token management
│   ├── infra.py            # Lakebase provisioner (project/branch/endpoint)
│   ├── api/
│   │   ├── main.py         # FastAPI app + routes
│   │   ├── schemas.py      # Pydantic request/response models
│   │   └── user.py         # User identity extraction
│   ├── core/
│   │   └── models.py       # Domain models
│   └── db/
│       ├── postgres.py     # Database client (psycopg + OAuth)
│       └── schemas.py      # SQLAlchemy ORM models (migration source of truth)
└── frontend/
    ├── package.json
    ├── vite.config.ts
    └── src/
        ├── App.tsx
        ├── main.tsx
        ├── index.css
        ├── api/client.ts
        └── types/api.ts
```

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (Python package manager)
- [Node.js](https://nodejs.org/) >= 18
- [Databricks CLI](https://docs.databricks.com/dev-tools/cli/index.html)
- **Can Manage** permission on the Lakebase project in your workspace

## Local Development

All configuration is auto-detected from the Databricks SDK — no `.env` file needed. The setup script provisions your personal Lakebase branch, creates the database, and runs migrations.

### 1. Clone and install dependencies

```bash
git clone <repo-url> && cd lakebase-todo-app
uv sync
cd frontend && npm install && cd ..
```

### 2. Authenticate with Databricks

```bash
databricks auth login --host https://your-workspace.cloud.databricks.com
```

### 3. Run the setup script

```bash
uv run python scripts/dev_setup.py
```

This will:
- Detect your identity from the Databricks SDK
- Create a personal Lakebase branch named `dev-{username}` (e.g., `dev-alex-lopez`)
- Provision the endpoint and Postgres role
- Run Alembic migrations (creates the `todoapp` database if it doesn't exist)

Override defaults with flags:

```bash
uv run python scripts/dev_setup.py --branch my-feature   # custom branch name
uv run python scripts/dev_setup.py --project my-project   # custom project ID
uv run python scripts/dev_setup.py --endpoint primary      # custom endpoint ID
uv run python scripts/dev_setup.py --skip-migrations       # skip alembic
```

### 4. Start the development servers

```bash
# Terminal 1 — Backend (FastAPI on port 8000)
uv run uvicorn app:app --reload --host 0.0.0.0 --port 8000

# Terminal 2 — Frontend (Vite dev server on port 5173, proxies /api to backend)
cd frontend && npm run dev
```

Open http://localhost:5173 in your browser.

> **Note:** The backend auto-detects `dev-{username}` from your Databricks identity — no configuration needed for the default branch. If you provisioned a custom branch with `--branch`, set `LAKEBASE_BRANCH_ID` when starting the backend (the setup script will show the exact command).

## Branching Strategy

Lakebase [branches](https://docs.databricks.com/en/lakebase/) provide isolated Postgres environments with independent data, endpoints, and migration state.

**`production`** is the single long-lived branch. The deployed app always connects to `production` (hardcoded in `app.yaml`), and CI runs migrations against it. This branch should never be deleted.

**Development branches** are short-lived and disposable. The setup script creates one per developer (defaulting to `dev-{username}`, configurable via `--branch`). Use them to iterate on schema changes and test locally without affecting production data. Delete them when you're done.

Schema changes flow through git (Alembic migrations), not through Lakebase branch merges. When you create a new migration, apply it to your dev branch locally, then CI applies it to `production` on merge:

```bash
uv run alembic upgrade head                                # your dev branch (auto-detected)
LAKEBASE_BRANCH_ID=production uv run alembic upgrade head  # production (CI handles this)
```

## API Endpoints

| Method   | Path                          | Description            |
|----------|-------------------------------|------------------------|
| `GET`    | `/api/health`                 | Health check           |
| `GET`    | `/api/me`                     | Current user info      |
| `POST`   | `/api/todos`                  | Create a todo          |
| `GET`    | `/api/todos`                  | List todos             |
| `GET`    | `/api/todos/{id}`             | Get a todo             |
| `PUT`    | `/api/todos/{id}`             | Update a todo          |
| `PATCH`  | `/api/todos/{id}/toggle`      | Toggle completion      |
| `DELETE` | `/api/todos/{id}`             | Delete a todo          |
| `GET`    | `/api/stats`                  | Todo statistics        |

## Database Migrations

Schema changes are managed with [Alembic](https://alembic.sqlalchemy.org/). The SQLAlchemy models in `src/todo_app/db/schemas.py` are the source of truth. The app checks for pending migrations on startup and logs a warning if the database is behind.

Alembic auto-detects your `dev-{username}` branch by default. If you provisioned a custom branch with `--branch`, prefix commands with `LAKEBASE_BRANCH_ID`:

```bash
# Default branch (auto-detected) — no prefix needed
uv run alembic upgrade head

# Custom branch — specify explicitly
LAKEBASE_BRANCH_ID=my-feature uv run alembic upgrade head
```

### Create a new migration

```bash
# Auto-generate from model changes
uv run alembic revision --autogenerate -m "describe your change"

# Or create an empty migration to write manually
uv run alembic revision -m "describe your change"
```

### Apply migrations

```bash
uv run alembic upgrade head      # Apply all pending migrations
uv run alembic upgrade +1        # Apply one migration forward
```

### Rollback migrations

```bash
uv run alembic downgrade -1      # Roll back one migration
uv run alembic downgrade base    # Roll back everything
```

### View migration status

```bash
uv run alembic current           # Show current revision
uv run alembic history           # Show migration history
uv run alembic heads             # Show latest revision
```

## CI/CD

GitHub Actions workflows handle continuous integration and deployment using **trunk-based development**:

| Workflow | Trigger | What it does |
|---|---|---|
| `ci.yml` | PR to `main` | Ruff lint, pytest, TypeScript typecheck, bundle validate |
| `deploy-dev.yml` | Push to `main` | Deploy bundle, provision Lakebase, run migrations, deploy app |
| `release-prod.yml` | Manual dispatch (main only) | Run tests, deploy to prod, create GitHub Release |

### Required GitHub configuration

**Secrets** (repository-level):
- `ARM_CLIENT_ID` — Azure Entra ID app registration client ID
- `ARM_CLIENT_SECRET` — Azure Entra ID app registration client secret value
- `ARM_TENANT_ID` — Azure AD tenant ID

**Variables** (repository-level):
- `DATABRICKS_HOST` — Databricks workspace URL (e.g., `https://adb-xxx.yy.azuredatabricks.net`)

### Bootstrap: Lakebase project permissions (manual step)

The CI service principal must be granted **Can Manage** on the Lakebase project before the deploy workflows can provision infrastructure or create Postgres roles. This permission cannot be set via API — it must be configured manually in the Databricks UI:

1. Navigate to the Lakebase project in the workspace
2. Open the project's **Permissions** settings
3. Add the CI service principal and grant **Can Manage**

This is a one-time setup step. Once granted, the `provision_ci()` method in `infra.py` handles everything else automatically: creating the Lakebase project/branch/endpoint, protecting the branch, and creating Postgres roles for both the CI service principal and the Databricks App service principal.
