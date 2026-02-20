"""Lakebase Autoscaling infrastructure provisioner."""

from __future__ import annotations

from dataclasses import dataclass

import structlog
from databricks.sdk import WorkspaceClient
from databricks.sdk.errors import AlreadyExists, BadRequest, NotFound
from databricks.sdk.service.postgres import (
    Branch,
    BranchSpec,
    Endpoint,
    EndpointSpec,
    EndpointType,
    Project,
    ProjectSpec,
    Role,
    RoleAuthMethod,
    RoleIdentityType,
    RoleRoleSpec,
)
from google.protobuf.duration_pb2 import Duration

logger = structlog.get_logger()


class _SnakeCaseFieldMask:
    """FieldMask that preserves snake_case paths.

    The protobuf FieldMask.ToJsonString() auto-converts to camelCase, but
    the Lakebase API expects snake_case field paths. This duck-typed wrapper
    implements ToJsonString() without the camelCase conversion.
    """

    def __init__(self, paths: list[str]):
        self._paths = paths

    def ToJsonString(self) -> str:  # noqa: N802
        return ",".join(self._paths)


@dataclass
class ProvisionResult:
    project_name: str
    branch_name: str
    endpoint_name: str
    host: str
    database: str


class LakebaseProvisioner:
    """Idempotent provisioner for Lakebase Autoscaling resources."""

    def __init__(self, w: WorkspaceClient | None = None):
        self._w = w or WorkspaceClient()

    def ensure_project(self, project_id: str) -> Project:
        name = f"projects/{project_id}"
        try:
            project = self._w.postgres.get_project(name=name)
            logger.info("project_exists", project=name)
            return project
        except NotFound:
            pass

        logger.info("creating_project", project=name)
        try:
            op = self._w.postgres.create_project(
                project=Project(spec=ProjectSpec(pg_version=17)),
                project_id=project_id,
            )
            project = op.wait()
            logger.info("project_created", project=project.name)
            return project
        except AlreadyExists:
            return self._w.postgres.get_project(name=name)

    def ensure_branch(self, project_id: str, branch_id: str) -> Branch:
        parent = f"projects/{project_id}"
        name = f"{parent}/branches/{branch_id}"
        try:
            branch = self._w.postgres.get_branch(name=name)
            logger.info("branch_exists", branch=name)
            return branch
        except NotFound:
            pass

        logger.info("creating_branch", branch=name)
        try:
            op = self._w.postgres.create_branch(
                parent=parent,
                branch=Branch(spec=BranchSpec(no_expiry=True)),
                branch_id=branch_id,
            )
            branch = op.wait()
            logger.info("branch_created", branch=branch.name)
            return branch
        except AlreadyExists:
            return self._w.postgres.get_branch(name=name)

    def protect_branch(self, project_id: str, branch_id: str) -> Branch | None:
        """Protect a branch from deletion and reset. Idempotent.

        Returns None if the branch cannot be protected (e.g., plan limit reached).
        """
        name = f"projects/{project_id}/branches/{branch_id}"
        branch = self._w.postgres.get_branch(name=name)
        if branch.spec and branch.spec.is_protected:
            logger.info("branch_already_protected", branch=name)
            return branch

        logger.info("protecting_branch", branch=name)
        try:
            op = self._w.postgres.update_branch(
                name=name,
                branch=Branch(name=name, spec=BranchSpec(is_protected=True)),
                update_mask=_SnakeCaseFieldMask(["spec.is_protected"]),
            )
            branch = op.wait()
            logger.info("branch_protected", branch=name)
            return branch
        except BadRequest as e:
            logger.warning("branch_protection_failed", branch=name, error=str(e))
            return None

    def ensure_endpoint(
        self,
        project_id: str,
        branch_id: str,
        endpoint_id: str,
        *,
        min_cu: float = 0.5,
        max_cu: float = 2.0,
        suspend_timeout_seconds: int = 300,
    ) -> Endpoint:
        parent = f"projects/{project_id}/branches/{branch_id}"
        name = f"{parent}/endpoints/{endpoint_id}"
        try:
            endpoint = self._w.postgres.get_endpoint(name=name)
            logger.info("endpoint_exists", endpoint=name)
            return endpoint
        except NotFound:
            pass

        logger.info("creating_endpoint", endpoint=name)
        try:
            op = self._w.postgres.create_endpoint(
                parent=parent,
                endpoint=Endpoint(
                    spec=EndpointSpec(
                        endpoint_type=EndpointType.ENDPOINT_TYPE_READ_WRITE,
                        autoscaling_limit_min_cu=min_cu,
                        autoscaling_limit_max_cu=max_cu,
                        suspend_timeout_duration=Duration(seconds=suspend_timeout_seconds),
                    ),
                ),
                endpoint_id=endpoint_id,
            )
            endpoint = op.wait()
            logger.info("endpoint_created", endpoint=endpoint.name)
            return endpoint
        except AlreadyExists:
            return self._w.postgres.get_endpoint(name=name)
        except BadRequest as e:
            if "already exists" not in str(e):
                raise
            # A read_write endpoint exists with a different ID (e.g. auto-provisioned
            # on the default production branch). Find it.
            logger.info("endpoint_exists_different_id", expected=name, error=str(e))
            for ep in self._w.postgres.list_endpoints(parent=parent):
                logger.info("endpoint_found", endpoint=ep.name)
                return ep
            raise

    def ensure_role(
        self,
        project_id: str,
        branch_id: str,
        postgres_role: str,
        identity_type: RoleIdentityType,
    ) -> Role | None:
        parent = f"projects/{project_id}/branches/{branch_id}"
        role_id = postgres_role.replace("@", "-").replace(".", "-").lower()
        # role_id must match ^[a-z]([a-z0-9-]{0,61}[a-z0-9])?$
        if role_id and not role_id[0].isalpha():
            role_id = f"sp-{role_id}"
        name = f"{parent}/roles/{role_id}"
        try:
            role = self._w.postgres.get_role(name=name)
            logger.info("role_exists", role=name)
            return role
        except NotFound:
            pass

        logger.info("creating_role", role=name)
        try:
            op = self._w.postgres.create_role(
                parent=parent,
                role=Role(
                    spec=RoleRoleSpec(
                        postgres_role=postgres_role,
                        identity_type=identity_type,
                        auth_method=RoleAuthMethod.LAKEBASE_OAUTH_V1,
                    ),
                ),
                role_id=role_id,
            )
            role = op.wait()
            logger.info("role_created", role=role.name)
            return role
        except (AlreadyExists, BadRequest) as e:
            logger.info("role_already_exists", role=name, error=str(e))
            return None

    def provision_all(
        self,
        user_email: str,
        *,
        project_id: str = "todo-app",
        branch_id: str = "production",
        endpoint_id: str = "default",
    ) -> ProvisionResult:
        self.ensure_project(project_id)
        self.ensure_branch(project_id, branch_id)
        endpoint = self.ensure_endpoint(project_id, branch_id, endpoint_id)
        self.ensure_role(project_id, branch_id, user_email, RoleIdentityType.USER)

        host = endpoint.status.hosts.host if endpoint.status and endpoint.status.hosts else ""
        endpoint_name = f"projects/{project_id}/branches/{branch_id}/endpoints/{endpoint_id}"

        return ProvisionResult(
            project_name=f"projects/{project_id}",
            branch_name=f"projects/{project_id}/branches/{branch_id}",
            endpoint_name=endpoint_name,
            host=host,
            database="postgres",
        )

    def ensure_database(
        self,
        endpoint: Endpoint,
        endpoint_name: str,
        database: str,
    ) -> None:
        """Create the application database if it doesn't exist."""
        import time

        import psycopg

        host = endpoint.status.hosts.host
        me = self._w.current_user.me()
        user = me.user_name
        cred = self._w.postgres.generate_database_credential(endpoint=endpoint_name)

        logger.info(
            "connecting_to_create_database",
            host=host,
            user=user,
            config_client_id=self._w.config.client_id,
            me_user_name=me.user_name,
            me_display_name=me.display_name,
            endpoint=endpoint_name,
            database=database,
            token_length=len(cred.token) if cred.token else 0,
        )

        last_error = None
        for attempt in range(3):
            if attempt > 0:
                logger.info("retrying_database_connection", attempt=attempt + 1, wait=5)
                time.sleep(5)
                cred = self._w.postgres.generate_database_credential(endpoint=endpoint_name)

            try:
                conn = psycopg.connect(
                    host=host,
                    port=5432,
                    dbname="postgres",
                    user=user,
                    password=cred.token,
                    sslmode="require",
                    autocommit=True,
                )
                try:
                    conn.execute(f"CREATE DATABASE {database}")
                    logger.info("database_created", database=database)
                except psycopg.errors.DuplicateDatabase:
                    logger.info("database_exists", database=database)
                finally:
                    conn.close()
                return
            except psycopg.OperationalError as e:
                last_error = e
                logger.warning("database_connection_failed", attempt=attempt + 1, error=str(e))

        raise last_error

    def provision_ci(
        self,
        *,
        project_id: str = "todo-app",
        branch_id: str = "production",
        endpoint_id: str = "primary",
        database: str = "todoapp",
        app_name: str | None = None,
    ) -> None:
        """Provision infrastructure for CI/CD.

        Ensures Lakebase resources exist, protects the branch, creates a role
        for the CI service principal, creates the application database, and
        optionally creates a role for the Databricks App service principal.
        """
        self.ensure_project(project_id)
        self.ensure_branch(project_id, branch_id)
        endpoint = self.ensure_endpoint(project_id, branch_id, endpoint_id)
        self.protect_branch(project_id, branch_id)

        # Create role for CI service principal (the identity running this code)
        me = self._w.current_user.me()
        ci_sp_id = (
            self._w.config.client_id
            or self._w.config.azure_client_id
        )
        if ci_sp_id:
            self.ensure_role(
                project_id, branch_id, me.user_name,
                RoleIdentityType.SERVICE_PRINCIPAL,
            )

        # Create role for the Databricks App service principal
        if app_name:
            app = self._w.apps.get(name=app_name)
            app_sp_id = app.service_principal_client_id
            if app_sp_id:
                self.ensure_role(
                    project_id, branch_id, app_sp_id, RoleIdentityType.SERVICE_PRINCIPAL
                )

        # Create application database (idempotent)
        endpoint_name = endpoint.name or f"projects/{project_id}/branches/{branch_id}/endpoints/{endpoint_id}"
        self.ensure_database(endpoint, endpoint_name, database)
