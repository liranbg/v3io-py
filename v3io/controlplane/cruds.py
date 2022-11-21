import abc
import typing
import pydantic

from v3io.controlplane.client import APIClient


class _CrudFactory:
    @staticmethod
    def create(crud_type: str) -> "_BaseCrud":
        if crud_type == "user":
            return _UserCrud
        else:
            raise Exception("Unknown type")


class _BaseCrud(pydantic.BaseModel, abc.ABC):
    __ALLOW_GET_DETAIL__ = True
    type: str = ""

    @classmethod
    async def create(cls, http_client: APIClient, attributes):
        return await http_client.create(cls._as_resource_name(), attributes)

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
    async def update(cls, http_client: APIClient, resource_id, attributes):
        await http_client.update(cls._as_resource_name(), resource_id, attributes)

    @classmethod
    async def delete(cls, http_client: APIClient, resource_id, ignore_missing=False):
        await http_client.delete(
            cls._as_resource_name(), resource_id, ignore_missing=ignore_missing
        )

    @classmethod
    def _as_resource_name(cls):
        return cls.__fields__["type"].default


class _UserCrud(_BaseCrud):
    type: str = "user"
