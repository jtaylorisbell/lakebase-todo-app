"""User identification from HTTP headers (Databricks Apps) or environment."""

from dataclasses import dataclass

from fastapi import Request

from todo_app.config import get_settings


@dataclass
class CurrentUser:
    email: str | None
    name: str | None

    @property
    def display_name(self) -> str:
        if self.name:
            return self.name
        if self.email:
            return self.email.split("@")[0]
        return "Unknown"

    @property
    def is_authenticated(self) -> bool:
        return bool(self.email)


def get_current_user(request: Request) -> CurrentUser:
    """Extract current user from Databricks Apps headers or env vars."""
    email = request.headers.get("X-Forwarded-Email")
    name = request.headers.get("X-Forwarded-Preferred-Username")

    if not email:
        settings = get_settings()
        email = settings.user.email or None
        name = name or settings.user.name or None

    return CurrentUser(email=email, name=name)
