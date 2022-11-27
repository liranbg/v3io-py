import unittest
import json

from v3io.controlplane import User, AccessKey, UserGroup, Job
from v3io.logger.logger import get_or_create_logger


# TODO: fix this test file
class TestCrud(unittest.TestCase):
    def setUp(self) -> None:
        self.logger = get_or_create_logger()
        self.logger.info_with("Starting test", test_id=self.id())
        self._crud_modules = [User, AccessKey, UserGroup, Job]

    def test_sanity(self):
        for model in self._crud_modules:
            self.logger.info_with("Testing model", model=model.__name__)
            dummy_data = getattr(self, f"_get_dummy_{model().type}")()

            instance = (
                model.from_orm(dummy_data)
                if model.__ALLOW_GET_DETAIL__
                else model.from_orm({"data": dummy_data["data"][0]})
            )

            dummy_data = (
                dummy_data["data"]
                if model.__ALLOW_GET_DETAIL__
                else dummy_data["data"][0]
            )
            self.assertEqual(dummy_data["id"], instance.id)
            for field, value in json.loads(
                instance.json(exclude_unset=True)
            ).items():
                self.assertEqual(dummy_data["attributes"][field], value)

    @staticmethod
    def _get_dummy_user():
        return {
            "data": {
                "type": "user",
                "id": "762ee2ca-d2bc-4329-9f5a-60f8eb3ac19f",
                "attributes": {
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
                },
                "relationships": {
                    "tenant": {
                        "data": {
                            "type": "tenant",
                            "id": "12345678-1234-5678-1234-567812345678",
                        }
                    }
                },
            },
            "included": [],
            "meta": {"ctx": "11068862825860294136"},
        }

    @staticmethod
    def _get_dummy_user_group():
        return {
            "data": {
                "type": "user_group",
                "id": "72f357e6-f3cb-4564-aeb9-35f13b1aaade",
                "attributes": {
                    "name": "some-group",
                    "data_access_mode": "enabled",
                    "gid": 70,
                    "kind": "local",
                    "assigned_policies": ["Data", "Application Admin"],
                    "system_provided": False,
                },
            },
            "included": [],
            "meta": {"ctx": "13751516721665979787"},
        }

    @staticmethod
    def _get_dummy_access_key():
        return {
            "data": {
                "type": "access_key",
                "id": "20573cbe-c81c-49bc-adbe-49bdd59ea1e7",
                "attributes": {
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
                },
            },
            "included": [],
            "meta": {"ctx": "10022211004627870368"},
        }

    @staticmethod
    def _get_dummy_app_services_manifest():
        return {
            "data": [
                {
                    "type": "app_services_manifest",
                    "id": 0,
                    "attributes": {
                        "cluster_name": "",
                        "tenant_name": "default-tenant",
                        "tenant_id": "b7c663b1-a8ee-49a9-ad62-ceae7e751ec8",
                        "app_services": [
                            {
                                "spec": {
                                    "desired_state": "ready",
                                    "kind": "jupyter",
                                    "name": "jupyter-somer_user",
                                    "advanced": {
                                        "priority_class_name": "igz-workload-medium",
                                    },
                                    "resources": {
                                        "limits": {"memory": "12Gi"},
                                        "requests": {"memory": "1.2Gi"},
                                    },
                                    "visible_to_all": False,
                                    "owner": "some_user",
                                    "mark_for_restart": False,
                                    "mark_as_changed": True,
                                },
                            },
                        ],
                        "state": "ready",
                        "last_modification_job": "e4c22a47-9227-4c0d-b43d-ee4f58f972ab",
                        "running_modification_job": "",
                    },
                }
            ],
            "included": [],
            "meta": {"ctx": "11480934097554558085"},
        }

    @staticmethod
    def _get_dummy_job():
        return {
            "data": {
                "type": "job",
                "id": "e4c22a47-9227-4c0d-b43d-ee4f58f972ab",
                "attributes": {
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
                },
            },
            "included": [],
            "meta": {"ctx": "10533417003758764105"},
        }
