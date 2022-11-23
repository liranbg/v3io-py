import unittest
import json

from v3io.controlplane import User, AccessKey, UserGroup, Job
from v3io.logger.logger import get_or_create_logger


class TestAttributes(unittest.TestCase):
    def setUp(self) -> None:
        self.logger = get_or_create_logger()
        self.logger.info_with("Starting test", test_id=self.id())
        self._models = [User, UserGroup, AccessKey, Job]

    def test_forward_compatible(self):
        for model in self._models:
            self.logger.info_with("Testing model", model=model.__name__)
            dummy_data = getattr(self, f"_get_dummy_{model.__name__.lower()}")()

            # imagine we get a field from BE that we don't know about yet (BE is new, SDK is old)
            instance = model(**dummy_data, some_new_field="some_value")
            self.assertEqual(instance.some_new_field, "some_value")
            json_instance = instance.json(exclude_unset=True)
            for field, value in json.loads(json_instance).items():
                if field == "some_new_field":
                    self.assertEqual(value, "some_value")
                    self.assertNotIn(field, dummy_data)
                    continue
                self.assertEqual(dummy_data[field], value)

    def test_backwards_compatible(self):
        for model in self._models:
            self.logger.info_with("Testing model", model=model.__name__)
            model()

    def test_sanity(self):
        for model in self._models:
            self.logger.info_with("Testing model", model=model.__name__)
            dummy_data = getattr(self, f"_get_dummy_{model.__name__.lower()}")()

            instance = model(**dummy_data)
            for field, value in json.loads(instance.json(exclude_unset=True)).items():
                self.assertEqual(dummy_data[field], value)

    @staticmethod
    def _get_dummy_user():
        return {
            "username": "someone",
            "first_name": "b",
            "last_name": "a",
            "email": "from@iguazio.com",
            "uid": 50,
            "created_at": "2022-10-23T17:14:18.839000+00:00",
            "data_access_mode": "enabled",
            "authentication_scheme": "local",
            "send_password_on_creation": False,
            "assigned_policies": [
                "Data",
                "Developer",
            ],
            "operational_status": "up",
            "admin_status": "up",
        }

    @staticmethod
    def _get_dummy_usergroup():
        return {
            "name": "some-group",
            "data_access_mode": "enabled",
            "gid": 70,
            "kind": "local",
            "assigned_policies": ["Data", "Application Admin"],
            "system_provided": False,
        }

    @staticmethod
    def _get_dummy_accesskey():
        return {
            "tenant_id": "b7c663b1-a8ee-49a9-ad62-ceae7e751ec8",
            "ttl": 315360000,
            "created_at": "2022-10-25T10:39:47.148000+00:00",
            "group_ids": [
                "09f902c9-f421-4868-ac9b-82af040f32db",
                "72f357e6-f3cb-4564-aeb9-35f13b1aaade",
            ],
            "uid": 0,
            "gids": [70],
            "expires_at": 1982054387,
            "interface_kind": "web",
            "kind": "accessKey",
            "planes": ["control", "data"],
        }

    @staticmethod
    def _get_dummy_job():
        return {
            "kind": "some.job.kind",
            "params": "",
            "max_total_execution_time": 10800,
            "max_worker_execution_time": 10800,
            "delay": 0.0,
            "state": "completed",
            "result": "Successfully completed something",
            "created_at": "2022-10-24T20:47:25.477000+00:00",
            "on_success": [],
            "on_failure": [],
            "updated_at": "2022-10-24T20:47:25.630000+00:00",
            "handler": "some.service.id",
            "ctx_id": "10533417003758764105",
        }
