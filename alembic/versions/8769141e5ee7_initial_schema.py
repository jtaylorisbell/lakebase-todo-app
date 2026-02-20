"""initial schema

Revision ID: 8769141e5ee7
Revises:
Create Date: 2026-02-19 11:50:33.581045

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '8769141e5ee7'
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "todos",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("completed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "priority",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'medium'"),
        ),
        sa.Column("user_email", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_todos_user_email", "todos", ["user_email"])
    op.create_index("idx_todos_completed", "todos", ["completed"])
    op.create_index("idx_todos_created_at", "todos", ["created_at"])


def downgrade() -> None:
    op.drop_index("idx_todos_created_at", table_name="todos")
    op.drop_index("idx_todos_completed", table_name="todos")
    op.drop_index("idx_todos_user_email", table_name="todos")
    op.drop_table("todos")
