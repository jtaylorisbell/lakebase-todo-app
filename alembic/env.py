"""Alembic environment configuration.

Builds the database URL dynamically using LakebaseSettings and OAuthTokenManager
so that migrations work with Databricks OAuth — no hardcoded credentials.

The database is created automatically if it doesn't exist (connects to the
default ``postgres`` database to run ``CREATE DATABASE``).
"""

from __future__ import annotations

import sys
from pathlib import Path
from urllib.parse import quote_plus

from alembic import context
from sqlalchemy import engine_from_config, pool

# Ensure src/ is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from todo_app.config import LakebaseSettings  # noqa: E402
from todo_app.db.schemas import Base  # noqa: E402

config = context.config
target_metadata = Base.metadata


def _get_settings() -> LakebaseSettings:
    return LakebaseSettings()


def _build_url(lb: LakebaseSettings, database: str | None = None) -> str:
    """Build a SQLAlchemy database URL from LakebaseSettings + OAuth."""
    host = lb.get_host()
    user = lb.get_user()
    password = lb.get_password()
    db = database or lb.database
    return (
        f"postgresql+psycopg2://{quote_plus(user)}:{quote_plus(password)}"
        f"@{host}:5432/{db}"
        f"?sslmode=require"
    )


def _ensure_database(lb: LakebaseSettings) -> None:
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
        conn.execute(f"CREATE DATABASE {lb.database}")
    except psycopg.errors.DuplicateDatabase:
        pass
    finally:
        conn.close()


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode — emits SQL to stdout."""
    lb = _get_settings()
    url = _build_url(lb)
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode — connects to the database."""
    lb = _get_settings()
    _ensure_database(lb)

    cfg = config.get_section(config.config_ini_section, {})
    cfg["sqlalchemy.url"] = _build_url(lb)

    connectable = engine_from_config(
        cfg,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
