"""PostgreSQL database client for Todo App."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

import psycopg
import structlog

from todo_app.config import _token_manager, get_settings

logger = structlog.get_logger()


class LakebaseConnectionFactory:
    """Factory for creating Lakebase connections with OAuth authentication."""

    def __init__(self):
        settings = get_settings()
        self._postgres_host = settings.lakebase.get_host()
        self._postgres_database = settings.lakebase.database
        self._postgres_username = settings.lakebase.get_user()
        self._endpoint_name = settings.lakebase.endpoint_name

        logger.info(
            "lakebase_factory_initialized",
            host=self._postgres_host,
            database=self._postgres_database,
            branch=settings.lakebase.get_branch_id(),
            user=self._postgres_username,
        )

    def get_connection(self) -> psycopg.Connection:
        token = _token_manager.get_token(endpoint_name=self._endpoint_name)

        return psycopg.connect(
            host=self._postgres_host,
            port=5432,
            dbname=self._postgres_database,
            user=self._postgres_username,
            password=token,
            sslmode="require",
        )


_factory: LakebaseConnectionFactory | None = None


def get_factory() -> LakebaseConnectionFactory:
    global _factory
    if _factory is None:
        _factory = LakebaseConnectionFactory()
    return _factory


class PostgresDB:
    """PostgreSQL database client using psycopg with OAuth."""

    def __init__(self):
        self._factory = get_factory()

    @contextmanager
    def session(self) -> Generator[psycopg.Connection, None, None]:
        conn = self._factory.get_connection()
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
                    """
                    INSERT INTO todos (title, description, priority, user_email)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id, title, description, completed, priority,
                              user_email, created_at, updated_at
                    """,
                    (title, description, priority, user_email),
                )
                row = cur.fetchone()

        return self._row_to_dict(row)

    def get_todo(self, todo_id: str) -> dict | None:
        with self.session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, title, description, completed, priority,
                           user_email, created_at, updated_at
                    FROM todos WHERE id = %s
                    """,
                    (todo_id,),
                )
                row = cur.fetchone()

        if row is None:
            return None
        return self._row_to_dict(row)

    def list_todos(
        self,
        user_email: str | None = None,
        completed: bool | None = None,
        limit: int = 100,
    ) -> list[dict]:
        conditions = []
        params: list = []

        if user_email is not None:
            conditions.append("user_email = %s")
            params.append(user_email)
        if completed is not None:
            conditions.append("completed = %s")
            params.append(completed)

        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)

        params.append(limit)

        with self.session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT id, title, description, completed, priority,
                           user_email, created_at, updated_at
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
                rows = cur.fetchall()

        return [self._row_to_dict(row) for row in rows]

    def update_todo(
        self,
        todo_id: str,
        title: str | None = None,
        description: str | None = None,
        completed: bool | None = None,
        priority: str | None = None,
    ) -> dict | None:
        updates = []
        params: list = []

        if title is not None:
            updates.append("title = %s")
            params.append(title)
        if description is not None:
            updates.append("description = %s")
            params.append(description)
        if completed is not None:
            updates.append("completed = %s")
            params.append(completed)
        if priority is not None:
            updates.append("priority = %s")
            params.append(priority)

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
                    RETURNING id, title, description, completed, priority,
                              user_email, created_at, updated_at
                    """,
                    params,
                )
                row = cur.fetchone()

        if row is None:
            return None
        return self._row_to_dict(row)

    def delete_todo(self, todo_id: str) -> bool:
        with self.session() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM todos WHERE id = %s", (todo_id,))
                return cur.rowcount > 0

    def get_stats(self, user_email: str | None = None) -> dict:
        where_clause = ""
        params: list = []
        if user_email:
            where_clause = "WHERE user_email = %s"
            params = [user_email]

        with self.session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT
                        COUNT(*) AS total,
                        COUNT(*) FILTER (WHERE completed = true) AS completed,
                        COUNT(*) FILTER (WHERE completed = false) AS pending,
                        COUNT(*) FILTER (WHERE priority = 'high' AND completed = false) AS high_priority
                    FROM todos
                    {where_clause}
                    """,
                    params,
                )
                row = cur.fetchone()

        return {
            "total": row[0],
            "completed": row[1],
            "pending": row[2],
            "high_priority": row[3],
        }

    @staticmethod
    def _row_to_dict(row: tuple) -> dict:
        return {
            "id": str(row[0]),
            "title": row[1],
            "description": row[2],
            "completed": row[3],
            "priority": row[4],
            "user_email": row[5],
            "created_at": row[6],
            "updated_at": row[7],
        }


_db: PostgresDB | None = None


def get_db() -> PostgresDB:
    global _db
    if _db is None:
        _db = PostgresDB()
    return _db
