"""Configuration management for Todo App."""

from __future__ import annotations

from datetime import datetime, timedelta
from functools import lru_cache
from typing import ClassVar

import structlog
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = structlog.get_logger()


class OAuthTokenManager:
    """Manages OAuth tokens for Lakebase with automatic refresh."""

    _instance: ClassVar["OAuthTokenManager | None"] = None
    _token: str | None = None
    _expires_at: datetime | None = None
    _endpoint_name: str | None = None

    def __new__(cls) -> "OAuthTokenManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def get_token(
        self,
        endpoint_name: str,
        force_refresh: bool = False,
    ) -> str | None:
        if not endpoint_name:
            return None

        if (
            not force_refresh
            and self._token
            and self._endpoint_name == endpoint_name
            and self._expires_at
            and datetime.now() < self._expires_at - timedelta(minutes=5)
        ):
            return self._token

        try:
            from databricks.sdk import WorkspaceClient

            logger.info("generating_oauth_token", endpoint=endpoint_name)
            w = WorkspaceClient()
            cred = w.postgres.generate_database_credential(endpoint=endpoint_name)

            self._token = cred.token
            self._endpoint_name = endpoint_name
            self._expires_at = datetime.now() + timedelta(minutes=55)
            return self._token

        except ImportError:
            logger.warning("databricks_sdk_not_installed")
            return None
        except Exception as e:
            logger.error("oauth_token_generation_failed", error=str(e))
            return None


_token_manager = OAuthTokenManager()


class LakebaseSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="LAKEBASE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database: str = "todoapp"
    user: str = "lakebase"
    password: str = ""
    project_id: str = "todo-app"
    branch_id: str = "main"
    endpoint_id: str = "default"

    @property
    def endpoint_name(self) -> str:
        return f"projects/{self.project_id}/branches/{self.branch_id}/endpoints/{self.endpoint_id}"

    def get_host(self) -> str:
        """Resolve the Postgres host dynamically from the Lakebase endpoint."""
        from databricks.sdk import WorkspaceClient

        w = WorkspaceClient()
        endpoint = w.postgres.get_endpoint(name=self.endpoint_name)
        return endpoint.status.hosts.host

    def get_password(self) -> str:
        """Get the database password, generating an OAuth token if needed."""
        if self.password:
            return self.password

        if self.project_id:
            token = _token_manager.get_token(endpoint_name=self.endpoint_name)
            if token:
                return token

        return self.password


class UserSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="USER_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    email: str = ""
    name: str = ""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    log_level: str = "INFO"

    @property
    def lakebase(self) -> LakebaseSettings:
        return LakebaseSettings()

    @property
    def user(self) -> UserSettings:
        return UserSettings()


@lru_cache
def get_settings() -> Settings:
    return Settings()
