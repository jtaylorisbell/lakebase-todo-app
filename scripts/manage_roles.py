#!/usr/bin/env python3
"""Create Postgres roles and grant database permissions.

This script handles the *database-level* permission layer:
  - Creates OAuth roles for team members via databricks_create_role()
  - Grants appropriate Postgres privileges (CONNECT, USAGE, SELECT, etc.)

Usage:
    uv run python manage_roles.py --analysts analyst1@co.com analyst2@co.com
    uv run python manage_roles.py --engineers eng1@co.com eng2@co.com
    uv run python manage_roles.py --readonly reader@co.com
    uv run python manage_roles.py --from-env          # reads TEAM_* from .env
"""

import argparse
import json
import os
import sys

from helpers import get_pg_connection


# ── SQL templates ────────────────────────────────

SQL_CREATE_ROLE = "SELECT databricks_create_role(%s, 'USER')"

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


def grant_permissions(cur, email: str, readonly: bool = False) -> None:
    """Grant Postgres permissions to a role."""
    role = _quote_role(email)
    template = SQL_GRANT_READONLY if readonly else SQL_GRANT_READWRITE
    sql = template.format(role=role)
    cur.execute(sql)
    mode = "read-only" if readonly else "read-write"
    print(f"  + Granted {mode} on public schema to {email}")


def provision_users(emails: list[str], readonly: bool = False) -> None:
    """Create roles and grant permissions for a list of users."""
    if not emails:
        return

    conn = get_pg_connection()
    conn.autocommit = True

    try:
        with conn.cursor() as cur:
            # Ensure the databricks_auth extension is available
            cur.execute("CREATE EXTENSION IF NOT EXISTS databricks_auth")
            for email in emails:
                print(f"\nProvisioning: {email}")
                ensure_role(cur, email)
                grant_permissions(cur, email, readonly=readonly)
    finally:
        conn.close()

    print("\nDone.")


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
        "--analysts",
        nargs="*",
        default=[],
        help="Emails for read-write access (same as --engineers).",
    )
    parser.add_argument(
        "--readonly",
        nargs="*",
        default=[],
        help="Emails for read-only access.",
    )
    parser.add_argument(
        "--from-env",
        action="store_true",
        help="Read TEAM_ENGINEERS and TEAM_ANALYSTS from .env as JSON arrays.",
    )
    args = parser.parse_args()

    engineers = list(args.engineers)
    analysts = list(args.analysts)
    readonly = list(args.readonly)

    if args.from_env:
        engineers += json.loads(os.getenv("TEAM_ENGINEERS", "[]"))
        analysts += json.loads(os.getenv("TEAM_ANALYSTS", "[]"))

    readwrite = list(set(engineers + analysts))

    if not readwrite and not readonly:
        parser.print_help()
        sys.exit(1)

    provision_users(readwrite, readonly=False)
    provision_users(readonly, readonly=True)


if __name__ == "__main__":
    main()
