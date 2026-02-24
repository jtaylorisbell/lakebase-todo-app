"""Lakebase developer branch provisioner.

Production infrastructure (project, branch, endpoint, branch protection) is
managed declaratively via Databricks Asset Bundles (resources/lakebase.yml).
Postgres roles for CI/CD are managed via SQL (scripts/manage_roles.py).

This module handles developer-specific branch provisioning for local
development, where branch names are dynamic (dev-{username}).
"""

from __future__ import annotations

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


class LakebaseProvisioner:
    """Idempotent provisioner for developer Lakebase branches.

    Used by dev_setup.py to create personal branches, endpoints, and roles.
    """

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
