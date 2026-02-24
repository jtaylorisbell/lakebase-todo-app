"""Manage Lakebase Postgres roles for CI/CD.

Creates OAuth roles and grants database permissions for service principals.
Connects via psycopg using the caller's OAuth token (the CI service principal,
which is the project owner and has databricks_superuser privileges).

The databricks_auth extension must already exist (created by Alembic migration).

Usage:
    uv run python scripts/manage_roles.py --app-name lakebase-todo-app-dev
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import psycopg
from databricks.sdk import WorkspaceClient

# Ensure src/ is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from todo_app.config import LakebaseSettings


def _connect(lb: LakebaseSettings) -> psycopg.Connection:
    """Connect to the application database using OAuth."""
    return psycopg.connect(
        host=lb.get_host(),
        port=5432,
        dbname=lb.database,
        user=lb.get_user(),
        password=lb.get_password(),
        sslmode="require",
        autocommit=True,
    )


def _ensure_role(conn: psycopg.Connection, identity: str, identity_type: str) -> None:
    """Create an OAuth role if it doesn't already exist."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM pg_roles WHERE rolname = %s",
            (identity,),
        )
        if cur.fetchone():
            print(f"  Role already exists: {identity}")
            return

    with conn.cursor() as cur:
        cur.execute("SELECT databricks_create_role(%s, %s)", (identity, identity_type))
    print(f"  Created role: {identity} ({identity_type})")


def _grant_app_permissions(conn: psycopg.Connection, role: str, database: str) -> None:
    """Grant the application service principal full access to the app database."""
    # quote_ident is not available via psycopg params for identifiers,
    # but these values come from trusted sources (Databricks API, not user input).
    quoted = f'"{role}"'
    grants = [
        f"GRANT CONNECT ON DATABASE {database} TO {quoted}",
        f"GRANT USAGE ON SCHEMA public TO {quoted}",
        f"GRANT CREATE ON SCHEMA public TO {quoted}",
        f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {quoted}",
        f"ALTER DEFAULT PRIVILEGES IN SCHEMA public"
        f" GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {quoted}",
        f"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {quoted}",
        f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO {quoted}",
    ]
    with conn.cursor() as cur:
        for sql in grants:
            cur.execute(sql)
    print(f"  Granted permissions on {database} to {quoted}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage Lakebase Postgres roles for CI/CD")
    parser.add_argument("--app-name", required=True, help="Databricks App name")
    args = parser.parse_args()

    w = WorkspaceClient()
    lb = LakebaseSettings()

    # Look up the App service principal's client ID
    app = w.apps.get(name=args.app_name)
    app_sp_id = app.service_principal_client_id
    if not app_sp_id:
        print(f"Warning: App '{args.app_name}' has no service principal. Skipping role creation.")
        return

    print(f"Managing roles for app '{args.app_name}' (SP: {app_sp_id})")
    conn = _connect(lb)
    try:
        _ensure_role(conn, app_sp_id, "SERVICE_PRINCIPAL")
        _grant_app_permissions(conn, app_sp_id, lb.database)
    finally:
        conn.close()

    print("Done.")


if __name__ == "__main__":
    main()
