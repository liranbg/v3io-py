from v3io.controlplane.client import APIClient
from v3io.controlplane.constants import ConfigTypes


# Below are classes which do not have a corresponding resource in the API
# but represent operations
class ClusterConfigurations(object):
    @classmethod
    async def reload(cls, http_client: "APIClient", config_type: ConfigTypes):
        await http_client.request_job(
            f"configurations/{config_type.value}/reloads",
            timeout=60 * 15,
        )
