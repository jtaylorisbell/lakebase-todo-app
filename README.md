# 🏗️ Lakebase Ops — End-to-End Automation Reference

A complete, working reference for **automating Databricks Lakebase Autoscaling** — from infrastructure provisioning and CI/CD pipelines to developer onboarding and branch-based workflows. Built around a full-stack To-Do app (FastAPI + React) as the working example.

> 🎉 **Lakebase Autoscaling** is now GA!

## 🎯 What this repo demonstrates

Lakebase Autoscaling is new and there aren't established patterns for managing it in production. This repo solves that by providing a complete, working reference for:

- **🔧 Infrastructure as Code** — Databricks Asset Bundles provision the Lakebase project and platform ACLs alongside the app in a single declarative config
- **🚀 Automated CI/CD** — GitHub Actions deploys the app + infrastructure, creates Postgres roles for service principals, runs migrations, and ships code — all via OAuth (no PATs)
- **👥 Developer onboarding** — Add an email to `databricks.yml` + `db/roles.yml`, deploy, and the developer gets platform permissions + Postgres roles + Data API access
- **🌿 Branch-per-developer isolation** — Each developer gets a copy-on-write Lakebase branch forked from production, with auto-detection so no config is needed
- **🔐 Two-layer permission model** — Platform ACLs (DABs) and Postgres roles (SQL scripts) are managed independently and automated through CI
- **📡 Data API (PostgREST)** — The app uses the Lakebase Data API instead of direct Postgres connections, with authenticator role grants managed automatically

The To-Do app itself is intentionally simple — the real value is the operational scaffolding around it.

---

## 📂 Repository Structure

```
lakebase-todo-app/
├── app.py                           # Entrypoint (adds src/ to path, imports FastAPI app)
├── app.yaml                         # Databricks Apps runtime config
├── databricks.yml                   # DAB config (app + Lakebase infra)
├── resources/
│   ├── todo_app.yml                 # App resource definition
│   └── lakebase.yml                 # Lakebase project + platform ACLs
├── pyproject.toml                   # Python deps (uv)
├── Makefile                         # Common workflow shortcuts
│
├── src/todo_app/                    # 🐍 Backend (FastAPI + Data API)
│   ├── config.py                    # LakebaseSettings — auto-detects branch, user, endpoint
│   ├── api/                         # FastAPI routes
│   └── db/                          # Data API client (PostgREST), schemas
│
├── frontend/                        # ⚛️ Frontend (React + Vite + Tailwind)
│   ├── src/
│   └── package.json
│
├── alembic/                         # 🗃️ Database migrations
│   ├── env.py                       # OAuth-aware, auto-resolves credentials
│   └── versions/
│
├── src/todo_app/cli/                # 🛠️ lbctl CLI (Typer)
│   ├── __init__.py                  # Root app — registers subcommands
│   └── roles.py                     # Postgres roles & Data API grants
├── db/
│   └── roles.yml                     # Desired-state role config (users + access levels)
│
└── .github/workflows/               # ⚡ CI/CD pipelines
    ├── deploy-dev.yml               # Push to main → deploy to dev
    └── release-prod.yml             # Manual → deploy to prod + GitHub release
```

---

## ✅ Prerequisites

| Tool | Version | Purpose |
|---|---|---|
| [uv](https://docs.astral.sh/uv/) | 0.4+ | Python package management |
| [Databricks CLI](https://docs.databricks.com/dev-tools/cli/install) | 0.287+ | Auth, bundle deploy |
| [Node.js](https://nodejs.org/) | 20+ | Frontend |

---

## 💻 Local Development

> **Prerequisite:** You need **CAN_MANAGE** permission on the Lakebase project to create branches and endpoints. An admin adds your email to `databricks.yml` permissions and deploys the bundle — see [👥 Developer onboarding](#-developer-onboarding).

### 1. Clone and install

```bash
git clone <repo-url> && cd lakebase-todo-app
uv sync --extra migrations --extra dev
cd frontend && npm install && cd ..
```

### 2. Authenticate

```bash
databricks auth login --host https://<workspace>.azuredatabricks.net --profile todo-app-dev
```

> [!TIP]
> The `--profile` flag saves your login credentials under a named profile. Create a `.env` file referencing it for easy reuse:
> ```
> DATABRICKS_CONFIG_PROFILE=todo-app-dev
> ```

### 3. Create your dev branch

```bash
make branch-create NAME=dev-<your-name>
```

This forks from `production` and creates a read-write endpoint with 0.5–2 CU.

> [!TIP]
> Periodically reset your dev branch to pull the latest schema and data from production:
> ```bash
> make branch-reset NAME=dev-<your-name>
> LAKEBASE_BRANCH_ID=dev-<your-name> uv run alembic upgrade head
> ```

### 4. Run migrations

```bash
LAKEBASE_BRANCH_ID=dev-<your-name> uv run alembic upgrade head
```

### 5. Enable the Data API

In the Lakebase UI, navigate to your dev branch endpoint and click **Enable Data API**.

### 6. Start the app

```bash
# Backend (auto-detects your dev branch from your email)
uv run uvicorn app:app --host 0.0.0.0 --port 8000

# Frontend (separate terminal)
cd frontend && npm run dev
```

- Backend: http://localhost:8000
- Frontend: http://localhost:5173

### 🔍 How auto-detection works

`LakebaseSettings` in `src/todo_app/config.py` resolves connection details via the Databricks SDK based on the caller's identity. The same logic runs locally and when deployed — no config changes needed.

| Setting | Local (user) | Deployed (service principal) |
|---|---|---|
| Branch | `dev-{username}` from email | `production` |
| Endpoint | `primary` | `primary` |
| Database | `databricks_postgres` | `databricks_postgres` |
| User | Your Databricks email | SP `client_id` |
| Password | OAuth token | OAuth token |

Set `LAKEBASE_BRANCH_ID` to override branch detection in either context.

---

## 🏗️ Infrastructure

Infrastructure is managed with **Databricks Asset Bundles** — the Lakebase project is declared in `resources/lakebase.yml`, platform ACLs in `databricks.yml`, and both are deployed via `databricks bundle deploy`. The CI service principal becomes the project owner and gets `databricks_superuser`.

### 👥 Developer onboarding

To give a new developer access:

1. **Platform access** — Add their email to `databricks.yml` permissions with `CAN_MANAGE`
2. **Database access** — Add their email to `db/roles.yml` with `access: readwrite`
3. Commit and push to main — the deploy pipeline handles everything (bundle deploy + role provisioning + migrations)
4. Have them follow the [💻 Local Development](#-local-development) steps above

### 🔐 Two permission layers

| Layer | Controls | Managed by |
|---|---|---|
| **Project ACLs** | Platform ops (create branches, manage endpoints) | `databricks.yml` |
| **Postgres roles** | Data access (SELECT, INSERT, etc.) + Data API | `lbctl roles sync` + `db/roles.yml` |

These are independent — CAN_MANAGE does not grant database access, and vice versa. Both are provisioned automatically by the deploy pipeline.

---

## ⚡ CI/CD

All workflows authenticate via a **Databricks-managed service principal** (`DATABRICKS_CLIENT_ID`, `DATABRICKS_CLIENT_SECRET`). No PATs, no manual token rotation.

### 🟢 Deploy to Dev (`deploy-dev.yml`)

Triggers on every push to `main`:

1. `databricks bundle deploy -t dev` — creates/updates the App + Lakebase project + ACLs
2. `lbctl roles sync --config ... --app ...` — syncs App SP + user Postgres roles to match desired state
3. `alembic upgrade head` — runs migrations on production branch
4. `databricks bundle run -t dev` — deploys app source code

### 🏷️ Release to Prod (`release-prod.yml`)

Manual trigger from `main` with a version number:

1. Runs tests (ruff + pytest)
2. Same deploy flow as dev but targeting `prod`
3. Creates a Git tag and GitHub Release

---

## 🗃️ Database Migrations

Alembic manages Postgres schema changes. The `alembic/env.py` resolves credentials via the Databricks SDK — no connection strings to manage.

```bash
# Apply all pending migrations
uv run alembic upgrade head

# Target a specific branch
LAKEBASE_BRANCH_ID=dev-taylor-isbell uv run alembic upgrade head

# Generate a new migration from model changes
uv run alembic revision --autogenerate -m "add_audit_log_table"

# Show current version
uv run alembic current

# Downgrade one step
uv run alembic downgrade -1
```

---

## 🛠️ CLI

### `lbctl` — Lakebase role management

Manages database-layer permissions — role creation, Postgres grants, and Data API authenticator setup. See [`src/todo_app/cli/README.md`](src/todo_app/cli/README.md) for full command reference.

```bash
uv run lbctl roles diff   --config db/roles.yml              # show drift
uv run lbctl roles sync   --config db/roles.yml --app <name> # reconcile
```

### `databricks postgres` — Branch lifecycle

Branch operations use the [Databricks CLI](https://docs.databricks.com/aws/en/dev-tools/cli/reference/postgres-commands) directly:

```bash
databricks postgres list-branches projects/todo-app
databricks postgres create-branch projects/todo-app dev-alex \
  --json '{"spec": {"source_branch": "projects/todo-app/branches/production", "no_expiry": true}}'
databricks postgres delete-branch projects/todo-app/branches/dev-alex
databricks api post /api/2.0/postgres/projects/todo-app/branches/dev-alex:reset --json '{}'
```

See the Makefile for shortcuts: `make branch-list`, `make branch-create NAME=dev-alex`, etc.

---

## 🤖 Claude Code Skills

This repo includes project-local [Claude Code skills](https://docs.anthropic.com/en/docs/claude-code/skills) in `.claude/skills/` that let you run common dev workflows conversationally. If you have [Claude Code](https://docs.anthropic.com/en/docs/claude-code/overview) installed, these skills are available automatically when you open the repo.

### Available skills

| Skill | What to say | What it does |
|---|---|---|
| **onboard-developer** | "Add jane.doe@databricks.com to the project" | Edits `databricks.yml` + `db/roles.yml` with correct formatting, validates no duplicates |
| **branch-manage** | "Create a dev branch for me" | Runs `make branch-create`, migrations, reminds about Data API |
| **db-migrate** | "Run migrations on my dev branch" | Targets the right branch with `LAKEBASE_BRANCH_ID`, runs Alembic |
| **roles-manage** | "Show role drift" or "Sync roles" | Runs `lbctl roles diff/sync`, edits `db/roles.yml` |
| **dev-server** | "Start the dev servers" | Launches backend (8000) + frontend (5173) in background |

### Examples

```
> Onboard alex.smith@databricks.com with readwrite access
  → Edits both config files, summarizes changes, reminds to push

> Create a dev branch for alex-smith
  → Runs make branch-create, runs migrations, reminds to enable Data API

> What's the migration status on dev-taylor-isbell?
  → Runs alembic current with the right LAKEBASE_BRANCH_ID

> Start the app locally
  → Launches both servers in background, shows status
```

---

## 🏛️ Architecture

```
┌─────────────────────────────────┐
│         Databricks App          │
│  ┌──────────┐  ┌─────────────┐  │
│  │  React   │  │   FastAPI   │  │
│  │ Frontend │──│   Backend   │  │
│  └──────────┘  └──────┬──────┘  │
└────────────────────────┼────────┘
                         │ Data API (PostgREST)
                         ▼
              ┌─────────────────────┐
              │  Lakebase Postgres  │
              │  ┌───────────────┐  │
              │  │  production   │  │  ← deployed app
              │  ├───────────────┤  │
              │  │  dev-taylor   │  │  ← local dev
              │  ├───────────────┤  │
              │  │  dev-alex     │  │  ← another developer
              │  └───────────────┘  │
              └─────────────────────┘
```

### 📡 Data API (PostgREST)

The backend uses the [Lakebase Data API](https://learn.microsoft.com/en-us/azure/databricks/oltp/projects/data-api) instead of direct Postgres connections. This is a PostgREST-compatible REST interface that auto-generates endpoints from your database schema.

- Must be **enabled per-endpoint** via the Lakebase UI
- Creates an `authenticator` Postgres role that assumes user identities
- Each user needs `GRANT "user@email" TO authenticator` (handled by `lbctl roles provision`)
- The project owner **cannot** use the Data API (authenticator can't assume superuser roles)

### 🌿 Branching

Lakebase branches are **copy-on-write** — creating a branch is instant and doesn't duplicate data. Each developer gets an isolated branch forked from production.

Auto-detection convention:
- **Service principals** → `production` branch
- **Users** → `dev-{username}` branch (derived from email)

---

## 📚 References

- [Lakebase Data API](https://learn.microsoft.com/en-us/azure/databricks/oltp/projects/data-api)
- [Lakebase API guide](https://learn.microsoft.com/en-us/azure/databricks/oltp/projects/api-usage)
- [Grant user access tutorial](https://learn.microsoft.com/en-us/azure/databricks/oltp/projects/grant-user-access-tutorial)
- [Branch-based dev workflow](https://learn.microsoft.com/en-us/azure/databricks/oltp/projects/dev-workflow-tutorial)
- [Databricks Apps deployment](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/deploy)
- [Alembic documentation](https://alembic.sqlalchemy.org/)
