import enum


class _BaseEnum(enum.Enum):
    @classmethod
    def all(cls):
        return [member.value for member in cls]


class SessionPlanes(_BaseEnum):
    data = "data"
    control = "control"


class TenantManagementRoles(enum.Enum):
    it_admin = "IT Admin"
    application_admin = "Application Admin"
    security_admin = "Security Admin"
    project_security_admin = "Project Security Admin"
    project_read_only = "Project Read Only"
    application_read_only = "Application Read Only"
    data = "Data"
    tenant_admin = "Tenant Admin"
    developer = "Developer"
    service_admin = "Service Admin"
    system_admin = "System Admin"

    @staticmethod
    def default_role():
        return [TenantManagementRoles.application_admin]


class ConfigTypes(enum.Enum):
    artifact_version_manifest = "artifact_version_manifest"
    events = "events"
    cluster = "cluster"
    app_services = "app_services"


class JobStates(enum.Enum):
    completed = "completed"
    failed = "failed"
    canceled = "canceled"
    in_progress = "in_progress"

    @staticmethod
    def terminal_states():
        return [
            JobStates.completed.value,
            JobStates.failed.value,
            JobStates.canceled.value,
        ]
