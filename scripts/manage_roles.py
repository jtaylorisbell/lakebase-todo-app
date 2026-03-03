#!/usr/bin/env python3
"""Create Postgres roles and grant database permissions.

This script handles the *database-level* permission layer:
  - Creates OAuth roles for team members via databricks_create_role()
  - Grants appropriate Postgres privileges (CONNECT, USAGE, SELECT, etc.)

Everything runs in the default ``databricks_postgres`` database where the
databricks_auth extension and application tables live.

Usage:
    uv run python manage_roles.py --engineers eng1@co.com eng2@co.com
    uv run python manage_roles.py --readonly reader@co.com
    uv run python manage_roles.py --app my-app-dev    # App SP role
    uv run python manage_roles.py --app my-app-dev --db-access scripts/db_access.json
"""

import argparse
import json
import sys

from helpers import get_pg_connection, get_workspace_client


# ── SQL templates ────────────────────────────────

SQL_CREATE_ROLE = "SELECT databricks_create_role(%s, 'USER')"
SQL_CREATE_SP_ROLE = "SELECT databricks_create_role(%s, 'SERVICE_PRINCIPAL')"

SQL_GRANT_READWRITE = """
-- Connect + schema access
GRANT CONNECT ON DATABASE databricks_postgres TO {role};
GRANT USAGE  ON SCHEMA public TO {role};
GRANT CREATE ON SCHEMA public TO {role};

-- Existing objects
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES    IN SCHEMA public TO {role};
GRANT USAGE, SELECT                  ON ALL SEQUENCES IN SCHEMA public TO {role};

-- Future objects
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES    TO {role};
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT USAGE, SELECT                  ON SEQUENCES TO {role};
"""

SQL_GRANT_READONLY = """
GRANT CONNECT ON DATABASE databricks_postgres TO {role};
GRANT USAGE   ON SCHEMA public TO {role};

GRANT SELECT ON ALL TABLES    IN SCHEMA public TO {role};
GRANT USAGE  ON ALL SEQUENCES IN SCHEMA public TO {role};

ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT ON TABLES    TO {role};
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT USAGE  ON SEQUENCES TO {role};
"""

# Data API: allow the authenticator role to assume each user's identity.
# Only works after the Data API has been enabled in the Lakebase UI.
SQL_GRANT_TO_AUTHENTICATOR = "GRANT {role} TO authenticator"


def _quote_role(email: str) -> str:
    """Postgres-quote a role name (email addresses need double-quoting)."""
    return f'"{email}"'


def ensure_role(cur, email: str) -> None:
    """Create the OAuth Postgres role if it doesn't already exist."""
    cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (email,))
    if cur.fetchone():
        print(f"  + Role already exists: {email}")
        return
    cur.execute(SQL_CREATE_ROLE, (email,))
    print(f"  + Created role: {email}")


def ensure_sp_role(cur, identity: str) -> None:
    """Create a SERVICE_PRINCIPAL Postgres role if it doesn't already exist."""
    cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (identity,))
    if cur.fetchone():
        print(f"  + SP role already exists: {identity}")
        return
    cur.execute(SQL_CREATE_SP_ROLE, (identity,))
    print(f"  + Created SP role: {identity}")


def grant_permissions(cur, email: str, readonly: bool = False) -> None:
    """Grant Postgres permissions to a role."""
    import psycopg2

    role = _quote_role(email)
    template = SQL_GRANT_READONLY if readonly else SQL_GRANT_READWRITE
    cur.execute(template.format(role=role))
    mode = "read-only" if readonly else "read-write"
    print(f"  + Granted {mode} on public schema to {email}")

    # Grant to Data API authenticator role (requires superuser / project owner)
    try:
        cur.execute(SQL_GRANT_TO_AUTHENTICATOR.format(role=role))
        print(f"  + Granted Data API access to {email}")
    except (psycopg2.errors.UndefinedObject, psycopg2.errors.InsufficientPrivilege) as e:
        if "authenticator" in str(e) and "UndefinedObject" in type(e).__name__:
            print(f"  ! Data API not enabled — skipping authenticator grant")
        else:
            print(f"  ! Authenticator grant requires superuser — run via CI")


def main():
    parser = argparse.ArgumentParser(
        description="Manage Lakebase Postgres roles and permissions."
    )
    parser.add_argument(
        "--engineers",
        nargs="*",
        default=[],
        help="Emails for read-write access.",
    )
    parser.add_argument(
        "--readonly",
        nargs="*",
        default=[],
        help="Emails for read-only access.",
    )
    parser.add_argument(
        "--db-access",
        metavar="PATH",
        help="Path to JSON file with 'readwrite' and 'readonly' email lists.",
    )
    parser.add_argument(
        "--app",
        metavar="APP_NAME",
        help="Create a SERVICE_PRINCIPAL role for the Databricks App SP.",
    )
    args = parser.parse_args()

    # ── Collect emails from all sources ──────────
    readwrite = list(args.engineers)
    readonly = list(args.readonly)

    if args.db_access:
        with open(args.db_access) as f:
            data = json.load(f)
        readwrite += data.get("readwrite", [])
        readonly += data.get("readonly", [])

    readwrite = list(set(readwrite))
    readonly = list(set(readonly))

    # ── Resolve App SP identity (if --app) ───────
    app_sp_id = None
    if args.app:
        w = get_workspace_client()
        app = w.apps.get(name=args.app)
        app_sp_id = app.service_principal_client_id
        if app_sp_id:
            print(f"App service principal ({args.app}): {app_sp_id}")
        else:
            print(f"Warning: App '{args.app}' has no service_principal_client_id")

    if not app_sp_id and not readwrite and not readonly:
        parser.print_help()
        sys.exit(1)

    # ── Single connection for all operations ─────
    conn = get_pg_connection()
    conn.autocommit = True

    try:
        with conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS databricks_auth")

            # App SP role
            if app_sp_id:
                print(f"\nProvisioning App SP: {app_sp_id}")
                ensure_sp_role(cur, app_sp_id)
                grant_permissions(cur, app_sp_id)

            # Read-write user roles
            for email in readwrite:
                print(f"\nProvisioning (read-write): {email}")
                ensure_role(cur, email)
                grant_permissions(cur, email)

            # Read-only user roles
            for email in readonly:
                print(f"\nProvisioning (read-only): {email}")
                ensure_role(cur, email)
                grant_permissions(cur, email, readonly=True)
    finally:
        conn.close()

    print("\nDone.")


if __name__ == "__main__":
    main()
