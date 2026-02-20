"""Developer environment setup for the Lakebase Todo App.

Provisions Lakebase infrastructure (branch, endpoint, role) and runs
migrations. All config is auto-detected from the Databricks SDK —
no .env file needed.

Usage:
    uv run python scripts/dev_setup.py                        # auto-detect everything
    uv run python scripts/dev_setup.py --branch my-feat       # custom branch name
    uv run python scripts/dev_setup.py --project my-project   # custom project
    uv run python scripts/dev_setup.py --endpoint primary     # custom endpoint ID
    uv run python scripts/dev_setup.py --skip-migrations      # skip alembic
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

# Ensure src/ is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.postgres import RoleIdentityType

from todo_app.infra import LakebaseProvisioner


def _derive_branch_id(w: WorkspaceClient) -> str:
    """Derive branch name from user identity: dev-{username}."""
    me = w.current_user.me()
    username = me.user_name.split("@")[0].replace(".", "-").lower()
    return f"dev-{username}"


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
    parser.add_argument("--branch", help="Branch name (default: dev-{username})")
    parser.add_argument("--project", default="todo-app", help="Lakebase project ID (default: todo-app)")
    parser.add_argument("--endpoint", default="default", help="Endpoint ID (default: default)")
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

    # Step 2: Resolve config from args
    branch_id = args.branch or _derive_branch_id(w)
    project_id = args.project
    endpoint_id = args.endpoint
    print(f"\nProvisioning Lakebase: {project_id}/{branch_id}/{endpoint_id}")

    # Step 3: Provision infrastructure (all idempotent)
    provisioner = LakebaseProvisioner(w)
    provisioner.ensure_project(project_id)
    provisioner.ensure_branch(project_id, branch_id)
    endpoint = provisioner.ensure_endpoint(project_id, branch_id, endpoint_id)
    provisioner.ensure_role(project_id, branch_id, me.user_name, RoleIdentityType.USER)

    host = endpoint.status.hosts.host if endpoint.status and endpoint.status.hosts else ""
    print(f"  Endpoint host: {host}")

    # Step 4: Run migrations (creates the database if it doesn't exist)
    if args.skip_migrations:
        print("\nSkipping migrations (--skip-migrations)")
    else:
        print("\nRunning migrations...")
        # Set env vars so alembic connects to the right branch/endpoint
        os.environ["LAKEBASE_PROJECT_ID"] = project_id
        os.environ["LAKEBASE_BRANCH_ID"] = branch_id
        os.environ["LAKEBASE_ENDPOINT_ID"] = endpoint_id
        _run_migrations()

    # Determine if the user overrode any defaults
    default_branch = _derive_branch_id(w)
    uses_defaults = (
        project_id == "todo-app"
        and branch_id == default_branch
        and endpoint_id == "default"
    )

    # Summary
    print("\n" + "=" * 60)
    print("Setup complete!")
    print("=" * 60)
    print(f"  Project:  {project_id}")
    print(f"  Branch:   {branch_id}")
    print(f"  Endpoint: {endpoint_id}")
    print(f"  Host:     {host}")
    print()
    print("Start your servers:")
    if uses_defaults:
        print("  # Terminal 1 — Backend (auto-detects your branch)")
        print("  uv run uvicorn app:app --reload --host 0.0.0.0 --port 8000")
    else:
        env_parts = []
        if project_id != "todo-app":
            env_parts.append(f"LAKEBASE_PROJECT_ID={project_id}")
        if branch_id != default_branch:
            env_parts.append(f"LAKEBASE_BRANCH_ID={branch_id}")
        if endpoint_id != "default":
            env_parts.append(f"LAKEBASE_ENDPOINT_ID={endpoint_id}")
        env_prefix = " ".join(env_parts)
        print("  # Terminal 1 — Backend (using your custom config)")
        print(f"  {env_prefix} uv run uvicorn app:app --reload --host 0.0.0.0 --port 8000")
    print()
    print("  # Terminal 2 — Frontend")
    print("  cd frontend && npm run dev")
    print()
    print("Open http://localhost:5173")


if __name__ == "__main__":
    main()
