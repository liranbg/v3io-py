import abc
import typing
import pydantic

from v3io.controlplane.client import APIClient


class _CrudFactory:
    @staticmethod
    def create(crud_type: str) -> "_BaseCrud":
        if crud_type == "user":
            return _UserCrud
        elif crud_type == "user_group":
            return _UserGroupCrud
        elif crud_type == "access_key":
            return _AccessKeyCrud
        elif crud_type == "job":
            return _JobCrud
        else:
            raise Exception("Unknown type")


class _BaseCrud(pydantic.BaseModel, abc.ABC):
    __ALLOW_GET_DETAIL__ = True
    type: str = ""

    @classmethod
    async def create(cls, http_client: APIClient, attributes, relationships=None):
        return await http_client.create(
            cls._as_resource_name(), attributes, relationships
        )

    @classmethod
    async def get(cls, http_client: APIClient, resource_id, **kwargs):
        if not cls.__ALLOW_GET_DETAIL__:
            response_list = await cls.list(http_client)
            return response_list[0]
        return await http_client.detail(cls._as_resource_name(), resource_id, **kwargs)

    @classmethod
    async def list(
        cls,
        http_client: APIClient,
        filter_by: typing.Optional[typing.Mapping[str, str]] = None,
    ):
        params = {}
        if filter_by:
            for key, value in filter_by.items():
                params[f"filter[{key}]"] = value
        return await http_client.list(cls._as_resource_name(), params=params)

    @classmethod
    async def update(
        cls, http_client: APIClient, resource_id, attributes, relationships=None
    ):
        await http_client.update(
            cls._as_resource_name(), resource_id, attributes, relationships
        )

    @classmethod
    async def delete(
        cls, http_client: APIClient, resource_id, ignore_missing: bool = False
    ):
        await http_client.delete(
            cls._as_resource_name(), resource_id, ignore_missing=ignore_missing
        )

    @classmethod
    async def get_custom(cls, http_client: APIClient, path, **kwargs):
        return await http_client.request("GET", path, **kwargs)

    @classmethod
    def _as_resource_name(cls):
        return cls.__fields__["type"].default


# TODO: why we need these classes?
class _UserCrud(_BaseCrud):
    type: str = "user"


class _UserGroupCrud(_BaseCrud):
    type: str = "user_group"


class _AccessKeyCrud(_BaseCrud):
    type: str = "access_key"


class _JobCrud(_BaseCrud):
    type: str = "job"
