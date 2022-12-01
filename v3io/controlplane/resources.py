import typing
import inflection

import pydantic
from pydantic import Field, SecretStr
from pydantic.utils import GetterDict

from v3io.controlplane.client import APIClient
from v3io.controlplane.constants import (
    TenantManagementRoles,
    SessionPlanes,
    ApplyServicesMode,
    ForceApplyAllMode,
)
from v3io.controlplane.cruds import _CrudFactory, _BaseCrud
from v3io.controlplane.app_services import AppServiceBase, AppServiceSpec
from v3io.controlplane.exceptions import (
    ResourceDeleteException,
    ResourceUpdateException,
    ResourceListException,
)


class _BaseResource(pydantic.BaseModel):
    type: str
    id: typing.Optional[typing.Union[int, str]]
    relationships: typing.Optional[dict]

    class Config:
        class _BaseGetter(GetterDict):
            def get(self, key: typing.Any, default: typing.Any = None) -> typing.Any:
                if key in ["id", "type"]:
                    return self._obj["data"][key]
                elif key == "relationships":
                    return self._obj["data"].get("relationships", {})
                elif key in self._obj["data"]["attributes"]:
                    return self._obj["data"]["attributes"][key]
                return default

        orm_mode = True
        use_enum_values = True
        getter_dict = _BaseGetter

        # be forward compatible
        extra = "allow"

    @classmethod
    def get_crud(cls) -> _BaseCrud:
        return _CrudFactory.create(
            inflection.underscore(cls.__fields__["type"].default)
        )

    @classmethod
    async def get(
        cls, http_client: APIClient, resource_id, include=None
    ) -> "_BaseResource":
        params = {}
        if include:
            params["include"] = ",".join(include)
        resource = await cls.get_crud().get(http_client, resource_id, params=params)
        return cls.from_orm(resource)

    @classmethod
    async def list(
        cls,
        http_client: APIClient,
        filter_by: typing.Optional[typing.Mapping[str, str]] = None,
    ) -> typing.List["_BaseResource"]:
        list_resource = await cls.get_crud().list(http_client, filter_by)
        return [cls.from_orm({"data": item}) for item in list_resource["data"]]

    async def update(
        self, http_client: APIClient, relationships=None
    ) -> "_BaseResource":
        await self.get_crud().update(
            http_client,
            self.id,
            attributes=self._fields_to_attributes(),
            relationships=relationships,
        )

        # TODO: build cls from response when BE will return the updated resource within the response body
        updated_resource = await self.get(http_client, self.id)
        self.__dict__.update(updated_resource)
        return self

    async def delete(self, http_client: APIClient, ignore_missing: bool = False):
        await self.get_crud().delete(http_client, self.id, ignore_missing)

    def _fields_to_attributes(self):
        return self.dict(
            exclude={"type", "relationships", "id"},
            exclude_none=True,
            exclude_unset=True,
        )


class User(_BaseResource):
    type: str = "user"
    username: str = ""
    first_name: str = ""
    last_name: str = ""
    email: str = ""
    uid: int = 0
    created_at: str = ""
    data_access_mode: str = ""
    authentication_scheme: str = ""
    send_password_on_creation: bool = False
    assigned_policies: typing.List[TenantManagementRoles] = []
    operational_status: str = ""
    admin_status: str = ""
    password: SecretStr = Field(None, exclude=True)

    @classmethod
    async def create(
        cls,
        http_client: APIClient,
        username: str,
        password: str,
        email: str,
        first_name: str,
        last_name: str,
        assigned_policies: typing.List[TenantManagementRoles] = None,
    ) -> "User":
        """
        Create a new user
        """
        assigned_policies = assigned_policies or [
            TenantManagementRoles.developer.value,
            TenantManagementRoles.application_read_only.value,
        ]
        created_resource = await cls.get_crud().create(
            http_client,
            attributes={
                "username": username,
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "password": password,
                "assigned_policies": assigned_policies,
            },
        )
        return cls.from_orm(created_resource)

    @classmethod
    async def self(cls, http_client: APIClient) -> "User":
        """
        Get the current user
        """
        user = await cls.get_crud().get_custom(http_client, "self")
        return cls.from_orm(user)

    async def add_to_group(self, http_client: APIClient, group_id: str):
        """
        Add a user to a group

        1. get the user
        2. add the group to the user
        3. update the user
        """
        user = await self.get(http_client, self.id, include=["user_groups"])
        if "user_groups" not in user.relationships:
            user.relationships["user_groups"] = {"data": []}
        if group_id not in [
            group["id"] for group in user.relationships["user_groups"]["data"]
        ]:
            user.relationships["user_groups"]["data"].append(
                {"id": group_id, "type": "user_group"}
            )
            await user.update(http_client, relationships=user.relationships)

    async def remove_from_group(self, http_client: APIClient, group_id: str):
        """
        Remove a user from a group
        """
        user = await self.get(http_client, self.id, include=["user_groups"])
        if "user_groups" in user.relationships:
            user.relationships["user_groups"]["data"] = [
                group
                for group in user.relationships["user_groups"]["data"]
                if group["id"] != group_id
            ]
            await user.update(http_client, relationships=user.relationships)


class UserGroup(_BaseResource):
    type: str = "user_group"
    name: str = ""
    description: str = None
    data_access_mode: str = "enabled"
    gid: int = 0
    kind: str = "local"
    assigned_policies: typing.List[TenantManagementRoles] = []
    system_provided: bool = False

    @classmethod
    async def create(
        cls,
        http_client: APIClient,
        name: str,
        assigned_policies: typing.List[TenantManagementRoles] = None,
        description: str = None,
        gid: int = None,
        user_ids=None,
    ) -> "UserGroup":
        """
        Create a new user
        :param http_client: APIClient instance
        :param name: The name of the user group
        :param assigned_policies: The assigned policies of the user group (optional)
        :param gid: The gid of the user group (optional, leave empty for auto-assign)
        :param description: The description of the user group (optional)
        :param user_ids: The user ids to add to the user group (optional)
        """
        if not assigned_policies:
            assigned_policies = [
                TenantManagementRoles.data.value,
                TenantManagementRoles.application_admin.value,
            ]
        relationships = {}
        if user_ids:
            relationships["users"] = {
                "data": [{"id": user_id, "type": "user"} for user_id in user_ids]
            }
        created_resource = await cls.get_crud().create(
            http_client,
            attributes={
                "name": name,
                "description": description,
                "gid": gid,
                "assigned_policies": assigned_policies,
            },
            relationships=relationships,
        )
        return cls.from_orm(created_resource)


class AccessKey(_BaseResource):
    type: str = "access_key"
    tenant_id: str = ""
    ttl: int = 315360000  # 10 years
    created_at: str = ""
    updated_at: str = ""
    group_ids: typing.List[str] = []
    uid: int = 0
    gids: typing.List[int] = []
    expires_at: int = 0  # EPOCH
    interface_kind: str = "web"
    label: str = ""
    kind: str = "accessKey"
    planes: typing.List[SessionPlanes] = SessionPlanes.all()

    @classmethod
    async def create(
        cls,
        http_client: APIClient,
        planes: typing.List[SessionPlanes] = SessionPlanes.all(),
        label: str = None,
    ):
        """
        Create a new user
        :param http_client: APIClient instance
        :param planes: The planes of the access key (optional)
        :param label: The label of the access key (optional)
        """
        created_resource = await cls.get_crud().create(
            http_client,
            attributes={
                "planes": planes,
                "label": label,
            },
        )
        return cls.from_orm(created_resource)


class Job(_BaseResource):
    type: str = "job"
    kind: str = ""
    params: str = ""
    max_total_execution_time: int = 3 * 60 * 60  # in seconds
    max_worker_execution_time: typing.Optional[int] = None  # in seconds
    delay: float = 0  # in seconds
    state: str = "created"
    result: str = ""
    created_at: str = ""
    on_success: typing.List[dict] = None
    on_failure: typing.List[dict] = None
    updated_at: str = ""
    handler: str = ""
    ctx_id: str = ""

    async def delete(self, http_client: APIClient, **kwargs):
        raise ResourceDeleteException

    async def update(self, http_client: APIClient, **kwargs):
        raise ResourceUpdateException


class AppServicesManifest(_BaseResource):
    type: str = "app_services_manifest"
    cluster_name: str = ""
    tenant_name: str = ""
    tenant_id: str = ""
    app_services: typing.List[AppServiceBase] = []
    state: str = ""
    last_error: typing.Optional[str]
    last_modification_job: str = ""
    apply_services_mode: typing.Optional[ApplyServicesMode]
    running_modification_job: str = ""
    force_apply_all_mode: typing.Optional[ForceApplyAllMode]

    async def delete(self, http_client: APIClient, **kwargs):
        raise ResourceDeleteException

    async def update(self, http_client: APIClient, **kwargs):
        raise ResourceUpdateException

    async def list(self, http_client: APIClient, **kwargs):
        raise ResourceListException

    @classmethod
    async def get(cls, http_client: APIClient, **kwargs) -> "AppServicesManifest":
        resource = await cls.get_crud().list(http_client)
        return [cls.from_orm({"data": item}) for item in resource["data"]][0]

    def find(
        self, app_service_spec_name: str, app_service_spec_kind: str
    ) -> (AppServiceSpec, int):
        position = 0
        for app_service in self.app_services:
            if (app_service.spec.name == app_service_spec_name) and (
                app_service.spec.kind == app_service_spec_kind
            ):
                return app_service.spec, position
            position += 1
        return None, -1

    def create_or_update(self, app_service_spec: AppServiceSpec):
        app_service_spec_obj, position = self.find(
            app_service_spec.name, app_service_spec.kind
        )
        if app_service_spec_obj:
            self.app_services[position].spec = app_service_spec
        else:
            self.app_services.append(AppServiceBase(spec=app_service_spec))
