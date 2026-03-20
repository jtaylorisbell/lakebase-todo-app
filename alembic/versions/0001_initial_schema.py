"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-03-20

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- Table ---
    op.create_table(
        "todos",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("completed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("priority", sa.Text(), nullable=False, server_default=sa.text("'medium'")),
        sa.Column("priority_order", sa.Integer(), nullable=False, server_default=sa.text("2")),
        sa.Column("user_email", sa.Text(), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_todos_user_email", "todos", ["user_email"])
    op.create_index("idx_todos_completed", "todos", ["completed"])
    op.create_index("idx_todos_created_at", "todos", ["created_at"])
    op.create_index("idx_todos_due_date", "todos", ["due_date"])

    # --- Triggers ---
    op.execute("""
        CREATE OR REPLACE FUNCTION set_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER trg_todos_updated_at
        BEFORE UPDATE ON todos
        FOR EACH ROW
        EXECUTE FUNCTION set_updated_at();
    """)
    op.execute("""
        CREATE OR REPLACE FUNCTION set_priority_order()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.priority_order = CASE NEW.priority
                WHEN 'high'   THEN 1
                WHEN 'medium' THEN 2
                WHEN 'low'    THEN 3
                ELSE 2
            END;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER trg_todos_priority_order
        BEFORE INSERT OR UPDATE OF priority ON todos
        FOR EACH ROW
        EXECUTE FUNCTION set_priority_order();
    """)

    # --- RPC functions ---
    op.execute("""
        CREATE OR REPLACE FUNCTION toggle_todo(todo_id UUID)
        RETURNS SETOF todos
        LANGUAGE sql
        SECURITY INVOKER
        AS $$
            UPDATE todos
            SET completed = NOT completed
            WHERE id = todo_id
            RETURNING *;
        $$;
    """)
    op.execute("""
        CREATE OR REPLACE FUNCTION todo_stats(user_email_filter TEXT DEFAULT NULL)
        RETURNS TABLE(
            total      BIGINT,
            completed  BIGINT,
            pending    BIGINT,
            high_priority BIGINT
        )
        LANGUAGE sql
        SECURITY INVOKER
        AS $$
            SELECT
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE completed = true)  AS completed,
                COUNT(*) FILTER (WHERE completed = false) AS pending,
                COUNT(*) FILTER (WHERE priority = 'high' AND completed = false) AS high_priority
            FROM todos
            WHERE user_email_filter IS NULL OR user_email = user_email_filter;
        $$;
    """)

    # --- Grants for Data API ---
    op.execute("CREATE EXTENSION IF NOT EXISTS databricks_auth;")
    op.execute("GRANT USAGE ON SCHEMA public TO PUBLIC;")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON todos TO PUBLIC;")
    op.execute("GRANT EXECUTE ON FUNCTION toggle_todo(UUID) TO PUBLIC;")
    op.execute("GRANT EXECUTE ON FUNCTION todo_stats(TEXT) TO PUBLIC;")


def downgrade() -> None:
    op.execute("REVOKE EXECUTE ON FUNCTION todo_stats(TEXT) FROM PUBLIC;")
    op.execute("REVOKE EXECUTE ON FUNCTION toggle_todo(UUID) FROM PUBLIC;")
    op.execute("REVOKE SELECT, INSERT, UPDATE, DELETE ON todos FROM PUBLIC;")
    op.execute("REVOKE USAGE ON SCHEMA public FROM PUBLIC;")
    op.execute("DROP FUNCTION IF EXISTS todo_stats(TEXT);")
    op.execute("DROP FUNCTION IF EXISTS toggle_todo(UUID);")
    op.execute("DROP TRIGGER IF EXISTS trg_todos_priority_order ON todos;")
    op.execute("DROP FUNCTION IF EXISTS set_priority_order();")
    op.execute("DROP TRIGGER IF EXISTS trg_todos_updated_at ON todos;")
    op.execute("DROP FUNCTION IF EXISTS set_updated_at();")
    op.drop_index("idx_todos_due_date", table_name="todos")
    op.drop_index("idx_todos_created_at", table_name="todos")
    op.drop_index("idx_todos_completed", table_name="todos")
    op.drop_index("idx_todos_user_email", table_name="todos")
    op.drop_table("todos")
