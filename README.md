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
├── sql/
│   └── postgres_tables.sql # Reference DDL (documentation only)
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

```bash
cp .env.example .env
```

Edit `.env` with your Databricks workspace and Lakebase details:

```env
DATABRICKS_HOST=https://your-workspace.cloud.databricks.com

LAKEBASE_PROJECT_ID=todo-app
LAKEBASE_BRANCH_ID=main
LAKEBASE_ENDPOINT_ID=default
LAKEBASE_HOST=your-endpoint-host.database.cloud.databricks.com
LAKEBASE_PORT=5432
LAKEBASE_DATABASE=postgres
LAKEBASE_USER=your.email@company.com
LAKEBASE_SSLMODE=require

USER_EMAIL=your.email@company.com
USER_NAME=Your Name
```

Authentication uses **OAuth via the Databricks SDK** — no personal access tokens needed. Make sure you're authenticated with the Databricks CLI (`databricks auth login --profile <profile>`).

### 3. Provision Lakebase infrastructure (first time only)

```bash
uv run python -c "
from todo_app.infra import LakebaseProvisioner
p = LakebaseProvisioner()
result = p.provision_all(user_email='your.email@company.com')
print(f'Endpoint host: {result.host}')
"
```

This idempotently creates the Lakebase project, branch, endpoint, and user role.

### 4. Run database migrations

```bash
uv run alembic upgrade head
```

To check current migration status:

```bash
uv run alembic current
```

### 5. Start the development servers

Run the backend and frontend in separate terminals:

```bash
# Terminal 1 — Backend (FastAPI on port 8000)
uv run uvicorn app:app --reload --host 0.0.0.0 --port 8000

# Terminal 2 — Frontend (Vite dev server on port 5173, proxies /api to backend)
cd frontend && npm run dev
```

Open http://localhost:5173 in your browser. The Vite dev server proxies all `/api` requests to the FastAPI backend.

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

Schema changes are managed with [Alembic](https://alembic.sqlalchemy.org/). The SQLAlchemy models in `src/todo_app/db/schemas.py` are the source of truth.

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

The app is deployed as a [Databricks App](https://docs.databricks.com/dev-tools/databricks-apps/) using [Databricks Asset Bundles](https://docs.databricks.com/dev-tools/bundles/).

### 1. Build the frontend

```bash
cd frontend && npm run build && cd ..
```

This outputs static files to `frontend/dist/`, which FastAPI serves at the root path.

### 2. Regenerate requirements.txt

If you've changed Python dependencies:

```bash
uv export --no-hashes --no-emit-project > requirements.txt
```

The Databricks Apps runtime installs from `requirements.txt`, not `pyproject.toml`.

### 3. Run migrations against the target database

```bash
uv run alembic upgrade head
```

### 4. Deploy with DAB

```bash
# Validate the bundle
databricks bundle validate -t dev

# Deploy to the dev target
databricks bundle deploy -t dev

# Deploy to production
databricks bundle deploy -t prod
```

The `databricks.yml` defines two targets:

- **dev** — uses the `fe-sandbox` workspace profile, deploys under your user directory
- **prod** — production mode, runs as the deploying user

### 5. Verify the deployment

Once deployed, the app is accessible at the URL shown in the Databricks Apps UI. You can also check:

```bash
databricks apps get lakebase-todo-app-dev
```

### Configuration on Databricks

Environment variables are set in `app.yaml` and injected at runtime. The app authenticates to Lakebase using the Databricks Apps service principal OAuth flow — no secrets to manage.

The DAB resource in `resources/todo_app.yml` requests the `sql` user API scope, which grants the app's service principal permission to generate database credentials.
