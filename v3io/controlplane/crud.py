import abc
import typing
import asyncio

import pydantic
from pydantic.utils import GetterDict
from pydantic import Field

from v3io.controlplane.client import APIClient
from v3io.controlplane.constants import (
    TenantManagementRoles,
    SessionPlanes,
    ConfigTypes,
)
from v3io.common.helpers import retry_until_successful

from v3io.controlplane.models.attributes import (
    User,
    UserGroup,
    AccessKey,
    Job,
)


class _Base(pydantic.BaseModel, abc.ABC):
    __ALLOW_GET_DETAIL__ = True

    type: str
    id: typing.Optional[typing.Union[int, str]]
    relationships: typing.Optional[dict]
    attributes: typing.Optional[dict]

    class Config:
        class _BaseGetter(GetterDict):
            def get(self, key: typing.Any, default: typing.Any = None) -> typing.Any:
                if key in ["id", "type", "attributes"]:
                    return self._obj["data"][key]
                elif key == "relationships":
                    return self._obj["data"].get("relationships", {})
                elif key in self._obj["data"]["attributes"]:
                    return self._obj["data"]["attributes"][key]
                return default

        orm_mode = True
        getter_dict = _BaseGetter

        # be forward compatible
        extra = "allow"

    @classmethod
    async def get(cls, client: "APIClient", resource_id, include=None):
        if not cls.__ALLOW_GET_DETAIL__:
            app_services = await cls.list(client)
            return app_services[0]

        params = {}
        if include:
            params["include"] = ",".join(include)
        return await cls._get(
            client,
            resource_id,
            params=params,
        )

    @classmethod
    async def list(
        cls,
        client: "APIClient",
        filter_by: typing.Optional[typing.Mapping[str, str]] = None,
    ):
        params = {}
        if filter_by:
            for key, value in filter_by.items():
                params[f"filter[{key}]"] = value
        return await cls._list(client, params=params)

    async def update(self, client: "APIClient", **kwargs) -> "_Base":
        updated = await self._update(client, self.id, **kwargs)
        self.attributes = updated.attributes
        return self

    def delete(
        self, client: "APIClient", ignore_missing=False, **kwargs
    ) -> typing.Coroutine:
        return self._delete(client, self.id, ignore_missing=ignore_missing, **kwargs)

    @classmethod
    async def _create(cls, client: "APIClient", **kwargs) -> "_Base":
        created_resource = await client.create(cls._as_resource_name(), **kwargs)
        return cls.from_orm(created_resource)

    @classmethod
    async def _get(cls, client: "APIClient", resource_id, **kwargs) -> "_Base":
        resource = await client.detail(cls._as_resource_name(), resource_id, **kwargs)
        return cls.from_orm(resource)

    @classmethod
    async def _get_custom(cls, client: "APIClient", path, **kwargs) -> "_Base":
        resource = await client.request("GET", path, **kwargs)
        return cls.from_orm(resource)

    @classmethod
    async def _update(
        cls, client: "APIClient", resource_id, **kwargs
    ) -> typing.Optional["_Base"]:
        skip_get_after_update = kwargs.pop("skip_get_after_update", False)
        await client.update(cls._as_resource_name(), resource_id, **kwargs)

        # TODO: build cls from response when BE will return the updated resource within the response body
        if skip_get_after_update:
            return None
        return await cls._get(client, resource_id)

    async def _delete(
        self, client: "APIClient", resource_id, ignore_missing=False, **kwargs
    ):
        await client.delete(
            self._as_resource_name(),
            resource_id,
            ignore_missing=ignore_missing,
            **kwargs,
        )

    @classmethod
    async def _list(cls, client: "APIClient", **kwargs) -> typing.List["_Base"]:
        list_resource = await client.list(cls._as_resource_name(), **kwargs)
        return [cls.from_orm({"data": item}) for item in list_resource["data"]]

    @classmethod
    def _as_resource_name(cls):
        return cls.__fields__["type"].default


class Users(_Base):
    type: str = "user"
    attributes: typing.Optional[User]

    @classmethod
    async def create(
        cls,
        client,
        *,
        username,
        password,
        email,
        first_name,
        last_name,
        assigned_policies=None,
    ):
        """
        Create a new user
        """
        assigned_policies = assigned_policies or [
            TenantManagementRoles.developer.value,
            TenantManagementRoles.application_read_only.value,
        ]
        return await cls._create(
            client,
            attributes={
                "username": username,
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "password": password,
                "assigned_policies": assigned_policies,
            },
        )

    @classmethod
    async def self(cls, client) -> "Users":
        """
        Get the current user
        """
        response = await cls._get_custom(client, "self")
        return response

    async def add_to_group(self, client, group_id: str):
        """
        Add a user to a group

        1. get the user
        2. add the group to the user
        3. update the user
        """
        user = await self.get(client, self.id, include=["user_groups"])

        if "user_groups" not in user.relationships:
            user.relationships["user_groups"] = {"data": []}
        if group_id not in [
            group["id"] for group in user.relationships["user_groups"]["data"]
        ]:
            user.relationships["user_groups"]["data"].append(
                {"id": group_id, "type": "user_group"}
            )
            await user.update(client, attributes={}, relationships=user.relationships)

    async def remove_from_group(self, client, group_id: str):
        """
        Remove a user from a group
        """
        user = await self.get(client, self.id, include=["user_groups"])
        if "user_groups" in user.relationships:
            user.relationships["user_groups"]["data"] = [
                group
                for group in user.relationships["user_groups"]["data"]
                if group["id"] != group_id
            ]
            await user.update(client, attributes={}, relationships=user.relationships)


class UserGroups(_Base):
    type: str = "user_group"
    attributes: UserGroup = Field(default_factory=dict)

    @classmethod
    async def create(
        cls,
        client,
        *,
        name,
        assigned_policies=None,
        description=None,
        gid=None,
        user_ids=None,
    ):
        """
        Create a new user
        :param client: APIClient instance
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
        response = await cls._create(
            client,
            attributes={
                "name": name,
                "description": description,
                "gid": gid,
                "assigned_policies": assigned_policies,
            },
            relationships=relationships,
        )
        return response


class AccessKeys(_Base):
    type: str = "access_key"
    attributes: AccessKey = Field(default_factory=dict)

    @classmethod
    async def create(cls, client, *, planes=None, label=None):
        """
        Create a new user
        :param client: APIClient instance
        :param planes: The planes of the access key (optional)
        :param label: The label of the access key (optional)
        """
        if not planes:
            planes = SessionPlanes.all()
        return await cls._create(
            client,
            attributes={
                "planes": planes,
                "label": label,
            },
        )


class AppServicesManifests(_Base):
    __ALLOW_GET_DETAIL__ = False

    type: str = "app_services_manifest"
    # attributes: AppServicesManifest = Field(default_factory=dict)

    def delete(self, client: "APIClient", **kwargs) -> typing.Coroutine:
        raise NotImplementedError("This resource is not delete-able")

    async def update(self, client: "APIClient", **kwargs) -> "_Base":
        wait_for_completion = kwargs.pop("wait_for_completion", False)
        kwargs.setdefault("attributes", self.attributes.dict())
        await self._update(client, "", skip_get_after_update=True, **kwargs)
        if wait_for_completion:
            await asyncio.sleep(5)
            return await self.wait_for_update_completion(client)

        return (await self.list(client))[0]

    async def wait_for_update_completion(self, client: "APIClient"):
        async def _wait_for_state():
            manifest: typing.List[AppServicesManifests] = await self.list(client)
            if manifest[0].attributes.state not in ["ready", "error"]:
                await asyncio.sleep(10)
                raise RuntimeError(
                    f"Waiting for apply services completion, current state: {manifest[0].attributes.state}"
                )
            return manifest[0]

        manifest = await retry_until_successful(
            1, 60 * 15, client._logger, True, _wait_for_state
        )
        if manifest.attributes.state != "ready":
            raise RuntimeError(
                f"State is {manifest.attributes.state} instead of 'ready'"
            )

        return manifest


class Jobs(_Base):
    attributes: Job = Field(default_factory=dict)
    type = "job"

    def delete(self, client: "APIClient", **kwargs) -> typing.Coroutine:
        raise RuntimeError("This resource is not delete-able")

    def update(self, client: "APIClient", **kwargs) -> "_Base":
        raise RuntimeError("This resource is not update-able")


# Below are classes which do not have a corresponding resource in the API
# but represent operations
class ClusterConfig(object):
    @classmethod
    async def reload(cls, client: "APIClient", config_type: ConfigTypes):
        await client.request_job(
            f"configurations/{config_type.value}/reloads", timeout=60 * 15
        )
