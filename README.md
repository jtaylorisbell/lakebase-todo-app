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
- [Databricks CLI](https://docs.databricks.com/dev-tools/cli/index.html) configured with a workspace profile
- A Databricks workspace with Lakebase enabled

## Local Development

### 1. Clone and install dependencies

```bash
git clone <repo-url> && cd lakebase-todo-app

# Python dependencies
uv sync

# Frontend dependencies
cd frontend && npm install && cd ..
```

### 2. Configure environment

Authenticate with the Databricks CLI and set the profile so the SDK can resolve your workspace:

```bash
databricks auth login --host https://your-workspace.cloud.databricks.com --profile my-profile
export DATABRICKS_CONFIG_PROFILE=my-profile
```

Then create your `.env`:

```bash
cp .env.example .env
```

Edit `.env` with your details:

```env
LAKEBASE_PROJECT_ID=todo-app
LAKEBASE_BRANCH_ID=local-dev
LAKEBASE_ENDPOINT_ID=default
LAKEBASE_DATABASE=todoapp
LAKEBASE_USER=your.email@company.com

USER_EMAIL=your.email@company.com
USER_NAME=Your Name
```

The endpoint host, port, SSL mode, and workspace URL are all resolved automatically from the Databricks SDK — no need to configure them.

### 3. Provision Lakebase infrastructure (first time only)

Provision the Lakebase project with both branches — `main` for the deployed app and `local-dev` for local development:

```bash
uv run python -c "
from todo_app.infra import LakebaseProvisioner
p = LakebaseProvisioner()

# Provision main branch (used by the deployed app)
result = p.provision_all(user_email='your.email@company.com')
print(f'main endpoint: {result.host}')

# Provision local-dev branch (used for local development)
p.ensure_branch('todo-app', 'local-dev')
p.ensure_endpoint('todo-app', 'local-dev', 'default')
print('local-dev branch provisioned')
"
```

Then create the `todoapp` database on each branch. The default `postgres` database restricts CREATE permissions, so a dedicated database is needed:

```bash
uv run python -c "
from todo_app.config import LakebaseSettings, _token_manager
import psycopg2

for branch in ['main', 'local-dev']:
    lb = LakebaseSettings(branch_id=branch)
    host = lb.get_host()
    token = lb.get_password()
    conn = psycopg2.connect(host=host, port=5432, dbname='postgres',
        user=lb.user, password=token, sslmode='require')
    conn.autocommit = True
    conn.cursor().execute('CREATE DATABASE todoapp')
    print(f'Created todoapp database on {branch} branch')
    conn.close()
"
```

### 4. Run database migrations

```bash
uv run alembic upgrade head
```

The app checks for pending migrations on startup and logs a warning if the database is behind — but it won't auto-migrate, so you always run migrations deliberately.

### 5. Start the development servers

Run the backend and frontend in separate terminals:

```bash
# Terminal 1 — Backend (FastAPI on port 8000)
uv run uvicorn app:app --reload --host 0.0.0.0 --port 8000

# Terminal 2 — Frontend (Vite dev server on port 5173, proxies /api to backend)
cd frontend && npm run dev
```

Open http://localhost:5173 in your browser. The Vite dev server proxies all `/api` requests to the FastAPI backend.

## Branching Strategy

The app uses [Lakebase branches](https://docs.databricks.com/en/lakebase/) to isolate local development from the deployed application:

| Branch | Used by | Configured in |
|---|---|---|
| `main` | Deployed Databricks App | `app.yaml` |
| `local-dev` | Local development | `.env` |

Each branch has its own endpoint, data, and migration state. Schema migrations must be applied to each branch independently. When you create a new migration, apply it to both:

```bash
uv run alembic upgrade head                          # local-dev (from .env)
LAKEBASE_BRANCH_ID=main uv run alembic upgrade head  # main
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

## Deploying to Databricks

The app is deployed as a [Databricks App](https://docs.databricks.com/dev-tools/databricks-apps/) using [Databricks Asset Bundles](https://docs.databricks.com/dev-tools/bundles/). The deployed app uses the `main` Lakebase branch.

### 1. Run migrations against the main branch

```bash
LAKEBASE_BRANCH_ID=main uv run alembic upgrade head
```

### 2. Keep requirements.txt up to date

Databricks Apps installs Python dependencies from `requirements.txt` (not `pyproject.toml`). After adding or updating dependencies with `uv`, regenerate it:

```bash
uv export --no-hashes --no-emit-project > requirements.txt
```

### 3. Deploy with DAB

Databricks Apps automatically runs `npm install`, `npm run build`, and `pip install -r requirements.txt` during deployment — no manual build step needed.

```bash
# Validate the bundle
databricks bundle validate -t dev

# Deploy to the dev target
databricks bundle deploy -t dev

# Run the app (deploys source code and starts it)
databricks bundle run -t dev todo_app

# Deploy to production
databricks bundle deploy -t prod
```

The `databricks.yml` defines two targets:

- **dev** — development environment
- **prod** — production environment

### 4. Verify the deployment

Once deployed, the app is accessible at the URL shown in the Databricks Apps UI. You can also check:

```bash
databricks apps get lakebase-todo-app-dev
```

### Configuration on Databricks

Environment variables are set in `app.yaml` and injected at runtime — including `LAKEBASE_BRANCH_ID=main`, which points the deployed app at the `main` branch. The app authenticates to Lakebase using the Databricks Apps service principal OAuth flow — no secrets to manage.

The DAB resource in `resources/todo_app.yml` requests the `sql` user API scope, which grants the app's service principal permission to generate database credentials.

## CI/CD

GitHub Actions workflows handle continuous integration and deployment using trunk-based development:

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
