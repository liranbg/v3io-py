import abc
import typing
import copy

import pydantic
from pydantic import Field, SecretStr
from pydantic.utils import GetterDict

from v3io.controlplane.client import APIClient
from v3io.controlplane.constants import TenantManagementRoles
from v3io.controlplane.cruds import _CrudFactory, _BaseCrud


class _BaseResource(pydantic.BaseModel, abc.ABC):
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
        getter_dict = _BaseGetter

        # be forward compatible
        extra = "allow"

    @staticmethod
    def get_crud(crud_type) -> _BaseCrud:
        return _CrudFactory.create(crud_type)

    # @classmethod
    # async def create(cls, http_client: APIClient) -> "_BaseResource":
    #     created_resource = await cls.get_crud(cls._as_resource_name()).create(http_client)
    #     return cls.from_orm(created_resource)

    @classmethod
    async def get(
        cls, http_client: APIClient, resource_id, include=None
    ) -> "_BaseResource":
        params = {}
        if include:
            params["include"] = ",".join(include)
        resource = await cls.get_crud(cls._as_resource_name()).get(
            http_client, resource_id, params=params
        )
        return cls.from_orm(resource)

    @classmethod
    async def list(
        cls,
        http_client: APIClient,
        filter_by: typing.Optional[typing.Mapping[str, str]] = None,
    ) -> typing.List["_BaseResource"]:
        list_resource = await cls.get_crud(cls._as_resource_name()).list(
            http_client, filter_by
        )
        return [cls.from_orm({"data": item}) for item in list_resource["data"]]

    async def update(self, http_client: APIClient) -> "_BaseResource":
        await self.get_crud(self.type).update(
            http_client, self.id, attributes=self._fields_to_attributes()
        )
        return await self.get(http_client, self.id)

    async def delete(self, http_client: APIClient, ignore_missing=False):
        await self.get_crud(self.type).delete(http_client, self.id, ignore_missing)

    @classmethod
    def _as_resource_name(cls):
        return cls.__fields__["type"].default

    def _fields_to_attributes(self):
        attributes = copy.deepcopy(self.__dict__)
        del attributes["type"]
        del attributes["id"]
        del attributes["relationships"]
        # TODO: remove this
        del attributes["assigned_policies"]
        return attributes


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

    # TODO: method params
    @classmethod
    async def create(
        cls,
        http_client: APIClient,
        username,
        password,
        email,
        first_name,
        last_name,
        assigned_policies=None,
    ) -> "User":
        """
        Create a new user
        """
        assigned_policies = assigned_policies or [
            TenantManagementRoles.developer.value,
            TenantManagementRoles.application_read_only.value,
        ]
        created_resource = await cls.get_crud(cls._as_resource_name()).create(
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
