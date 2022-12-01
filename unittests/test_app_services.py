import unittest
import mock

from v3io.logger.logger import get_or_create_logger
from v3io.controlplane import AppServicesManifest, AppServiceBase, AppServiceSpec, JupyterSpec
from v3io.controlplane.exceptions import (
    ResourceDeleteException,
    ResourceUpdateException,
    ResourceListException,
)


class TestAppServices(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.logger = get_or_create_logger()
        self.logger.info_with("Starting test", test_id=self.id())
        self.client = mock.Mock()

    async def test_list_delete_update_get_app_services_manifest(self):
        with mock.patch('v3io.controlplane.AppServicesManifest.get', return_value=self._get_dummy_app_services_manifest()):
            app_services_manifest = await AppServicesManifest.get(
                self.client
            )
            self.assertNotEqual(0, len(app_services_manifest.app_services))

            with self.assertRaises(ResourceDeleteException):
                await app_services_manifest.delete(self.client)

            with self.assertRaises(ResourceUpdateException):
                await app_services_manifest.update(self.client)

            with self.assertRaises(ResourceListException):
                await app_services_manifest.list(self.client)

    async def test_create_jupyter_app_service(self):
        jupyter = AppServiceSpec(name="my-jupyter", owner="admin",
                                                   service_spec=JupyterSpec(image_name="jupyter-all"))

        self.assertEqual(jupyter.name, "my-jupyter")
        self.assertEqual(jupyter.owner, "admin")

        # check if kind value was injected
        self.assertEqual(jupyter.kind, "jupyter")
        self.assertEqual(jupyter.service_spec.image_name, "jupyter-all")

        with mock.patch('v3io.controlplane.AppServicesManifest.get',
                        return_value=self._get_dummy_app_services_manifest()):
            app_services_manifest = await AppServicesManifest.get(
                self.client
            )

            app_services_manifest.create_or_update(jupyter)

            # app services name not exists
            app_service_spec, position = app_services_manifest.find("not-exists-jupyter-app_service", "jupyter")
            self.assertIsNone(app_service_spec)
            self.assertEqual(position, -1)

            # app service name exist but wrong kind
            app_service_spec, position = app_services_manifest.find("my-jupyter", "dex")
            self.assertIsNone(app_service_spec)
            self.assertEqual(position, -1)

            # app service exists
            app_service_spec, position = app_services_manifest.find("my-jupyter", "jupyter")
            self.assertIsNotNone(app_service_spec)
            self.assertNotEqual(position, -1)
            self.assertEqual(app_service_spec.name, "my-jupyter")
            self.assertEqual(app_service_spec.kind, "jupyter")

    @staticmethod
    def _get_dummy_app_services_manifest():
        return AppServicesManifest(
            app_services=[
              AppServiceBase(spec=AppServiceSpec(name="my-jupyter", owner="admin", service_spec=JupyterSpec(image_name="jupyter-all")))
            ]
        )
