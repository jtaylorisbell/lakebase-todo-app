"""Developer environment setup for the Lakebase Todo App.

Provisions Lakebase infrastructure (branch, endpoint, role, database) and
runs migrations. All config is auto-detected from the Databricks SDK —
no .env file needed.

Usage:
    uv run python scripts/dev_setup.py                    # auto-detect everything
    uv run python scripts/dev_setup.py --branch my-feat   # custom branch name
    uv run python scripts/dev_setup.py --skip-migrations  # skip alembic
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

# Ensure src/ is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.postgres import RoleIdentityType

from todo_app.config import LakebaseSettings
from todo_app.infra import LakebaseProvisioner


def _derive_branch_id(w: WorkspaceClient) -> str:
    """Derive branch name from user identity: dev-{username}."""
    me = w.current_user.me()
    username = me.user_name.split("@")[0].replace(".", "-").lower()
    return f"dev-{username}"


def _create_database(lb: LakebaseSettings, database: str) -> None:
    """Create the application database if it doesn't exist."""
    import psycopg

    host = lb.get_host()
    user = lb.get_user()
    password = lb.get_password()

    conn = psycopg.connect(
        host=host,
        port=5432,
        dbname="postgres",
        user=user,
        password=password,
        sslmode="require",
        autocommit=True,
    )
    try:
        conn.execute(f"CREATE DATABASE {database}")
        print(f"  Created database '{database}'")
    except psycopg.errors.DuplicateDatabase:
        print(f"  Database '{database}' already exists")
    finally:
        conn.close()


def _run_migrations() -> None:
    """Run alembic upgrade head."""
    project_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=project_root,
    )
    if result.returncode != 0:
        print("\nMigrations failed. You can retry with:")
        print("  uv run alembic upgrade head")
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Set up local dev environment")
    parser.add_argument("--branch", help="Custom branch name (default: dev-{username})")
    parser.add_argument(
        "--skip-migrations", action="store_true", help="Skip running alembic migrations"
    )
    args = parser.parse_args()

    # Step 1: Validate Databricks auth
    print("Validating Databricks authentication...")
    try:
        w = WorkspaceClient()
        me = w.current_user.me()
        print(f"  Authenticated as: {me.user_name}")
    except Exception as e:
        print(f"  Authentication failed: {e}")
        print("\nRun: databricks auth login --host https://your-workspace.cloud.databricks.com")
        sys.exit(1)

    # Step 2: Derive branch name
    branch_id = args.branch or _derive_branch_id(w)
    project_id = "todo-app"
    endpoint_id = "default"
    database = "todoapp"
    print(f"\nProvisioning Lakebase branch: {branch_id}")

    # Step 3: Provision infrastructure (all idempotent)
    provisioner = LakebaseProvisioner(w)
    provisioner.ensure_project(project_id)
    provisioner.ensure_branch(project_id, branch_id)
    endpoint = provisioner.ensure_endpoint(project_id, branch_id, endpoint_id)
    provisioner.ensure_role(project_id, branch_id, me.user_name, RoleIdentityType.USER)

    host = endpoint.status.hosts.host if endpoint.status and endpoint.status.hosts else ""
    print(f"  Endpoint host: {host}")

    # Step 4: Create application database
    print(f"\nCreating database '{database}'...")
    lb = LakebaseSettings(branch_id=branch_id)
    _create_database(lb, database)

    # Step 5: Run migrations
    if args.skip_migrations:
        print("\nSkipping migrations (--skip-migrations)")
    else:
        print("\nRunning migrations...")
        # Set branch so alembic auto-detects the right endpoint
        import os

        os.environ["LAKEBASE_BRANCH_ID"] = branch_id
        _run_migrations()

    # Summary
    print("\n" + "=" * 60)
    print("Setup complete!")
    print("=" * 60)
    print(f"  Branch:   {branch_id}")
    print(f"  Database: {database}")
    print(f"  Host:     {host}")
    print()
    print("Start your servers:")
    print("  # Terminal 1 — Backend")
    print("  uv run uvicorn app:app --reload --host 0.0.0.0 --port 8000")
    print()
    print("  # Terminal 2 — Frontend")
    print("  cd frontend && npm run dev")
    print()
    print("Open http://localhost:5173")


if __name__ == "__main__":
    main()
