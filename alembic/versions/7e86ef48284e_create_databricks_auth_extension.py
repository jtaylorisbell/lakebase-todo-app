"""create databricks_auth extension

Revision ID: 7e86ef48284e
Revises: 8769141e5ee7
Create Date: 2026-02-24 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7e86ef48284e"
down_revision: str | None = "8769141e5ee7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS databricks_auth")


def downgrade() -> None:
    op.execute("DROP EXTENSION IF EXISTS databricks_auth")
