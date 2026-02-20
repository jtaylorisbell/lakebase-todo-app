"""PostgreSQL database client for Todo App."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

import psycopg
import structlog

from todo_app.config import _token_manager, get_settings

logger = structlog.get_logger()

_TODO_COLUMNS = "id, title, description, completed, priority, user_email, created_at, updated_at"


class PostgresDB:
    """PostgreSQL database client using psycopg with OAuth."""

    def __init__(self):
        settings = get_settings()
        self._host = settings.lakebase.get_host()
        self._database = settings.lakebase.database
        self._user = settings.lakebase.get_user()
        self._endpoint_name = settings.lakebase.get_endpoint_name()

        logger.info(
            "postgres_db_initialized",
            host=self._host,
            database=self._database,
            branch=settings.lakebase.get_branch_id(),
            user=self._user,
        )

    def _connect(self) -> psycopg.Connection:
        token = _token_manager.get_token(endpoint_name=self._endpoint_name)
        return psycopg.connect(
            host=self._host,
            port=5432,
            dbname=self._database,
            user=self._user,
            password=token,
            sslmode="require",
        )

    @contextmanager
    def session(self) -> Generator[psycopg.Connection, None, None]:
        conn = self._connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def health_check(self) -> bool:
        try:
            with self.session() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error("database_health_check_failed", error=str(e))
            return False

    # --- Todo CRUD ---

    def create_todo(
        self,
        title: str,
        description: str | None = None,
        priority: str = "medium",
        user_email: str | None = None,
    ) -> dict:
        with self.session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    INSERT INTO todos (title, description, priority, user_email)
                    VALUES (%s, %s, %s, %s)
                    RETURNING {_TODO_COLUMNS}
                    """,
                    (title, description, priority, user_email),
                )
                return self._row_to_dict(cur.fetchone())

    def get_todo(self, todo_id: str) -> dict | None:
        with self.session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT {_TODO_COLUMNS} FROM todos WHERE id = %s",
                    (todo_id,),
                )
                row = cur.fetchone()
        return self._row_to_dict(row) if row else None

    def list_todos(
        self,
        user_email: str | None = None,
        completed: bool | None = None,
        limit: int = 100,
    ) -> list[dict]:
        conditions: list[str] = []
        params: list = []

        if user_email is not None:
            conditions.append("user_email = %s")
            params.append(user_email)
        if completed is not None:
            conditions.append("completed = %s")
            params.append(completed)

        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
        params.append(limit)

        with self.session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT {_TODO_COLUMNS}
                    FROM todos
                    {where_clause}
                    ORDER BY
                        completed ASC,
                        CASE priority
                            WHEN 'high' THEN 1
                            WHEN 'medium' THEN 2
                            WHEN 'low' THEN 3
                        END,
                        created_at DESC
                    LIMIT %s
                    """,
                    params,
                )
                return [self._row_to_dict(row) for row in cur.fetchall()]

    def update_todo(
        self,
        todo_id: str,
        title: str | None = None,
        description: str | None = None,
        completed: bool | None = None,
        priority: str | None = None,
    ) -> dict | None:
        fields = {
            "title": title, "description": description,
            "completed": completed, "priority": priority,
        }
        updates = [f"{k} = %s" for k, v in fields.items() if v is not None]
        params = [v for v in fields.values() if v is not None]

        if not updates:
            return self.get_todo(todo_id)

        updates.append("updated_at = NOW()")
        params.append(todo_id)

        with self.session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    UPDATE todos
                    SET {", ".join(updates)}
                    WHERE id = %s
                    RETURNING {_TODO_COLUMNS}
                    """,
                    params,
                )
                row = cur.fetchone()
        return self._row_to_dict(row) if row else None

    def delete_todo(self, todo_id: str) -> bool:
        with self.session() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM todos WHERE id = %s", (todo_id,))
                return cur.rowcount > 0

    def get_stats(self, user_email: str | None = None) -> dict:
        where_clause = "WHERE user_email = %s" if user_email else ""
        params = [user_email] if user_email else []

        with self.session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT
                        COUNT(*) AS total,
                        COUNT(*) FILTER (WHERE completed = true) AS completed,
                        COUNT(*) FILTER (WHERE completed = false) AS pending,
                        COUNT(*) FILTER (
                            WHERE priority = 'high' AND completed = false
                        ) AS high_priority
                    FROM todos
                    {where_clause}
                    """,
                    params,
                )
                total, completed, pending, high_priority = cur.fetchone()
        return {
            "total": total,
            "completed": completed,
            "pending": pending,
            "high_priority": high_priority,
        }

    @staticmethod
    def _row_to_dict(row: tuple) -> dict:
        keys = (
            "id", "title", "description", "completed",
            "priority", "user_email", "created_at", "updated_at",
        )
        result = dict(zip(keys, row))
        result["id"] = str(result["id"])
        return result


_db: PostgresDB | None = None


def get_db() -> PostgresDB:
    global _db
    if _db is None:
        _db = PostgresDB()
    return _db
