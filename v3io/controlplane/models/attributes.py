import abc
import typing
import datetime

import pydantic
from pydantic import Field, SecretStr

from v3io.controlplane.constants import TenantManagementRoles, SessionPlanes


class _Base(pydantic.BaseModel, abc.ABC):
    class Config:
        extra = pydantic.Extra.allow


class User(_Base):
    username: str = Field(default="")
    first_name: str = Field(default="")
    last_name: str = Field(default="")
    email: str = Field(default="")
    uid: int = Field(default=0)
    created_at: str = Field(default="")
    data_access_mode: str = Field(default="")
    authentication_scheme: str = Field(default="")
    send_password_on_creation: bool = Field(default=False)
    assigned_policies: typing.List[TenantManagementRoles] = Field(default=[])
    operational_status: str = Field(default="")
    admin_status: str = Field(default="")
    password: SecretStr = Field(None, exclude=True)


class UserGroup(_Base):
    name: str = Field(default="")
    description: str = Field(None)
    data_access_mode: str = Field(default="enabled")
    gid: int = Field(default=0)
    kind: str = Field(default="local")
    assigned_policies: typing.List[TenantManagementRoles] = Field(default=[])
    system_provided: bool = Field(default=False)


class AccessKey(_Base):
    tenant_id: str = Field(default="")
    ttl: int = Field(default=315360000)  # 10 years
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    updated_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    group_ids: typing.List[str] = Field(default=[])
    uid: int = Field(default=0)
    gids: typing.List[int] = Field(default=[])
    expires_at: int = Field(default=0)  # EPOCH
    interface_kind: str = Field(default="web")
    label: str = Field(default="")
    kind: str = Field(default="accessKey")
    planes: typing.List[SessionPlanes] = Field(default=[SessionPlanes.all()])


class Job(_Base):
    kind: str = Field(default="")
    params: str = Field(default="")
    max_total_execution_time: int = Field(default=3 * 60 * 60)  # in seconds
    max_worker_execution_time: typing.Optional[int] = Field(default=None)  # in seconds
    delay: float = Field(default=0)  # in seconds
    state: str = Field(default="created")
    result: str = Field(default="")
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    on_success: typing.List[dict] = Field(default=None)
    on_failure: typing.List[dict] = Field(default=None)
    updated_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    handler: str = Field(default="")
    ctx_id: str = Field(default="")
