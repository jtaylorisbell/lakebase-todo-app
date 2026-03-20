"""Lakebase Data API client (PostgREST-compatible)."""

from __future__ import annotations

from functools import lru_cache

import httpx
import structlog

from todo_app.config import get_settings

logger = structlog.get_logger()


class DataAPIError(Exception):
    """Raised when a Data API request fails."""

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"Data API error {status_code}: {detail}")


class DataAPIClient:
    """HTTP client for the Lakebase Data API (PostgREST)."""

    def __init__(self, base_url: str):
        self._base_url = base_url
        self._client = httpx.Client(timeout=30.0)

    def _headers(self, *, prefer: str | None = None) -> dict[str, str]:
        from todo_app.config import LakebaseSettings

        token = LakebaseSettings().get_password()
        headers: dict[str, str] = {"Authorization": f"Bearer {token}"}
        if prefer:
            headers["Prefer"] = prefer
        return headers

    def _raise_for_status(self, resp: httpx.Response) -> None:
        if resp.is_success:
            return
        try:
            body = resp.json()
            detail = body.get("message") or body.get("details") or resp.text
        except Exception:
            detail = resp.text
        raise DataAPIError(resp.status_code, detail)

    # --- CRUD operations ---

    def create_todo(
        self,
        *,
        title: str,
        description: str | None = None,
        priority: str = "medium",
        due_date: str | None = None,
        user_email: str,
    ) -> dict:
        payload: dict = {
            "title": title,
            "priority": priority,
            "user_email": user_email,
        }
        if description is not None:
            payload["description"] = description
        if due_date is not None:
            payload["due_date"] = due_date

        resp = self._client.post(
            f"{self._base_url}/public/todos",
            json=payload,
            headers=self._headers(prefer="return=representation"),
        )
        self._raise_for_status(resp)
        rows = resp.json()
        return rows[0]

    def get_todo(self, todo_id: str) -> dict | None:
        resp = self._client.get(
            f"{self._base_url}/public/todos",
            params={"id": f"eq.{todo_id}"},
            headers=self._headers(),
        )
        self._raise_for_status(resp)
        rows = resp.json()
        return rows[0] if rows else None

    def list_todos(
        self,
        *,
        user_email: str | None = None,
        completed: bool | None = None,
        limit: int = 100,
    ) -> list[dict]:
        params: dict[str, str] = {
            "order": "completed.asc,priority_order.asc,created_at.desc",
            "limit": str(limit),
        }
        if user_email is not None:
            params["user_email"] = f"eq.{user_email}"
        if completed is not None:
            params["completed"] = f"eq.{str(completed).lower()}"

        resp = self._client.get(
            f"{self._base_url}/public/todos",
            params=params,
            headers=self._headers(),
        )
        self._raise_for_status(resp)
        return resp.json()

    def update_todo(
        self,
        todo_id: str,
        *,
        title: str | None = None,
        description: str | None = None,
        completed: bool | None = None,
        priority: str | None = None,
        due_date: str | None = None,
    ) -> dict | None:
        payload: dict = {}
        if title is not None:
            payload["title"] = title
        if description is not None:
            payload["description"] = description
        if completed is not None:
            payload["completed"] = completed
        if priority is not None:
            payload["priority"] = priority
        if due_date is not None:
            payload["due_date"] = due_date

        if not payload:
            return self.get_todo(todo_id)

        resp = self._client.patch(
            f"{self._base_url}/public/todos",
            params={"id": f"eq.{todo_id}"},
            json=payload,
            headers=self._headers(prefer="return=representation"),
        )
        self._raise_for_status(resp)
        rows = resp.json()
        return rows[0] if rows else None

    def delete_todo(self, todo_id: str) -> bool:
        resp = self._client.delete(
            f"{self._base_url}/public/todos",
            params={"id": f"eq.{todo_id}"},
            headers=self._headers(prefer="return=representation"),
        )
        self._raise_for_status(resp)
        rows = resp.json()
        return len(rows) > 0

    def toggle_todo(self, todo_id: str) -> dict | None:
        resp = self._client.post(
            f"{self._base_url}/rpc/toggle_todo",
            json={"todo_id": todo_id},
            headers=self._headers(prefer="return=representation"),
        )
        self._raise_for_status(resp)
        rows = resp.json()
        return rows[0] if rows else None

    def get_stats(self, *, user_email: str | None = None) -> dict:
        resp = self._client.post(
            f"{self._base_url}/rpc/todo_stats",
            json={"user_email_filter": user_email} if user_email else {},
            headers=self._headers(),
        )
        self._raise_for_status(resp)
        rows = resp.json()
        if rows:
            return rows[0]
        return {"total": 0, "completed": 0, "pending": 0, "high_priority": 0}

    def health_check(self) -> bool:
        try:
            resp = self._client.get(
                f"{self._base_url}/public/todos",
                params={"limit": "0"},
                headers=self._headers(),
            )
            return resp.is_success
        except Exception as e:
            logger.error("data_api_health_check_failed", error=str(e))
            return False


_client: DataAPIClient | None = None


@lru_cache
def get_data_api() -> DataAPIClient:
    settings = get_settings()
    base_url = settings.lakebase.get_data_api_url()
    logger.info("data_api_client_initialized", base_url=base_url)
    return DataAPIClient(base_url)
