import enum


class _BaseEnum(enum.Enum):
    @classmethod
    def all(cls):
        return [member.value for member in cls]


class _BaseEnumStr(str, _BaseEnum):
    pass


class SessionPlanes(_BaseEnumStr):
    data = "data"
    control = "control"


class TenantManagementRoles(_BaseEnumStr):
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


class ConfigTypes(_BaseEnumStr):
    artifact_version_manifest = "artifact_version_manifest"
    events = "events"
    cluster = "cluster"
    app_services = "app_services"


class JobStates(_BaseEnumStr):
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
