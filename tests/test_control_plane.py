import unittest
import os

import dotenv

import v3io.controlplane

# import v3io.controlplane.models
import v3io.controlplane.constants

# import v3io.controlplane.client
import v3io.common.helpers
import v3io.logger.logger

"""
This test is meant to be run against a live v3io control plane.
To be able to run it, you need to set the following environment variables to be set on `hack/env/dev`
API_URL
TEST_USERNAME
TEST_PASSWORD
TEST_PRIVILEGED_USERNAME
TEST_PRIVILEGED_PASSWORD
"""


class TestControlPlane(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.logger = v3io.logger.logger.get_or_create_logger("DEBUG", "test_logger")
        cls.config = dotenv.dotenv_values(f"hack/env/{os.getenv('TEST_ENV', 'dev')}")

    async def asyncSetUp(self):
        self.logger.info_with("Starting test", test_name=self._testMethodName)
        self.api_url = self.config["API_URL"]
        self.test_username = self.config["TEST_USERNAME"]
        self.client = await self._create_test_client()
        self._resources_to_delete = []

    async def asyncTearDown(self):
        self.logger.info_with("Tearing down test", test_name=self._testMethodName)
        for resource_to_delete in self._resources_to_delete:
            await resource_to_delete.delete(self.client, ignore_missing=True)
        await self.client.close()

    async def test_custom_endpoint(self):
        versions = await self.client.request("GET", "/versions")
        self.assertNotEqual(0, len(versions))

    async def test_get_list_delete_update_jobs(self):
        client = await self._create_test_privilege_client()
        jobs = await v3io.controlplane.Job.list(client)
        self.assertNotEqual(0, len(jobs))
        job = await v3io.controlplane.Job.get(client, jobs[0].id)
        self.assertEqual(jobs[0].id, job.id)

        with self.assertRaises(RuntimeError) as exc:
            await job.delete(client)
        self.assertEqual(
            str(exc.exception),
            "This resource is not delete-able",
        )

        with self.assertRaises(RuntimeError) as exc:
            await job.update(client)
        self.assertEqual(
            str(exc.exception),
            "This resource is not update-able",
        )

        await client.close()

    async def test_create_list_get_update_delete_access_keys(self):

        # create access key
        access_key = await v3io.controlplane.AccessKey.create(self.client)
        self._resources_to_delete.append(access_key)
        self.assertNotEqual("", access_key.id)

        # list access keys
        access_keys = await v3io.controlplane.AccessKey.list(self.client)
        self.assertNotEqual(0, len(access_keys))

        # get access key
        access_key = await v3io.controlplane.AccessKey.get(self.client, access_key.id)
        self.assertNotEqual("", access_key.id)

        # update access key
        # TODO - fix Object of type datetime is not JSON serializable
        # access_key.label = "my-awesome-label"
        # await access_key.update(self.client)
        # self.assertEqual("my-awesome-label", access_key.label)

        # delete access key
        await access_key.delete(self.client)

    async def test_list_users(self):
        users = await v3io.controlplane.User.list(self.client)
        self.assertNotEqual(0, len(users))

        # list users filter by username
        users = await v3io.controlplane.User.list(
            self.client, filter_by={"username": self.test_username}
        )
        self.assertEqual(1, len(users))
        self.assertEqual(self.test_username, users[0].username)

        user = await v3io.controlplane.User.get(self.client, users[0].id)
        self.assertEqual(users[0].username, user.username)

    async def test_authenticate_with_access_key(self):
        access_key = await v3io.controlplane.AccessKey.create(
            self.client,
            planes=[v3io.controlplane.constants.SessionPlanes.control],
            label="test",
        )
        self.assertNotEqual("", access_key.id)
        self._resources_to_delete.append(access_key)

        client = v3io.controlplane.client.APIClient(
            endpoint=self.api_url, username=self.test_username, access_key=access_key.id
        )
        user = await v3io.controlplane.User.self(client)
        self.assertEqual(self.test_username, user.username)
        await client.close()

    async def test_get_self(self):
        me = await v3io.controlplane.User.self(self.client)
        self.assertEqual(self.test_username, me.username)

    async def test_create_update_user(self):
        password = v3io.common.helpers.random_string(8) + "A1!"
        user = await self._create_dummy_user(password=password)

        user.first_name = "liran2"
        await user.update(self.client)
        self.assertEqual(user.first_name, "liran2")

    async def test_add_remove_from_user_group(self):
        # create user group
        group_name = v3io.common.helpers.random_string(8)
        user_group = await v3io.controlplane.UserGroup.create(
            self.client, name=group_name
        )
        self._resources_to_delete.append(user_group)
        self.assertEqual(group_name, user_group.name)
        self.assertNotEqual("", user_group.id)

        # create user
        user = await self._create_dummy_user()

        user_group = await v3io.controlplane.UserGroup.get(
            self.client, user_group.id, include=["users"]
        )
        self.assertEqual(0, len(user_group.relationships))

        # add user to group
        await user.add_to_group(self.client, user_group.id)

        # get user group and verify user is in it
        user_group = await v3io.controlplane.UserGroup.get(self.client, user_group.id, include=["users"])
        self.assertEqual(1, len(user_group.relationships["users"]["data"]))

        # remove user from group
        await user.remove_from_group(self.client, user_group.id)

        # get user group and verify user is NOT in it
        user_group = await v3io.controlplane.UserGroup.get(self.client, user_group.id, include=["users"])
        self.assertEqual(0, len(user_group.relationships))

        # delete user
        await user.delete(self.client)

        # delete user group
        await user_group.delete(self.client)

    async def test_misc(self):
        client = await self._create_test_privilege_client()
        await v3io.controlplane.Configurations.reload(client, v3io.controlplane.constants.ConfigTypes.events)
        await client.close()

    async def _create_dummy_user(self, username=None, password=None) -> "User":
        username = (
            v3io.common.helpers.random_string(10) if username is None else username
        )
        password = (
            v3io.common.helpers.random_string(8) + "A1!"
            if password is None
            else password
        )
        user = await v3io.controlplane.User.create(
            self.client,
            username=username,
            password=password,
            email=f"{username}@iguazio.com",
            first_name="liran",
            last_name="aa",
        )
        self._resources_to_delete.append(user)
        self.assertEqual(username, user.username)
        return user

    async def _create_test_privilege_client(self):
        client = v3io.controlplane.client.APIClient(endpoint=self.api_url)
        await client.login(
            username=self.config["TEST_PRIVILEGED_USERNAME"],
            password=self.config["TEST_PRIVILEGED_PASSWORD"],
        )
        return client

    async def _create_test_client(self):
        client = v3io.controlplane.client.APIClient(endpoint=self.api_url)
        await client.login(
            username=self.test_username, password=self.config["TEST_PASSWORD"]
        )
        return client
