import copy
import json
import base64
import os

import httpx

import inflection

from v3io.common.helpers import (
    retry_until_successful,
    RetryUntilSuccessfulInProgressErrorMessage,
)
import v3io.logger.logger

from .constants import SessionPlanes, JobStates


class _BaseHTTPClient:
    def __init__(
        self,
        parent_logger: v3io.logger.logger.Logger,
        api_url: str,
        *,
        timeout: int = 60,
        retries: int = 3,
    ) -> None:
        super().__init__()
        self._logger = parent_logger.get_child("httpc")
        self._transport = httpx.AsyncHTTPTransport(verify=False, retries=retries)
        self._cookies = httpx.Cookies()
        self._headers = {"Content-Type": "application/json"}
        self._session = httpx.AsyncClient(
            base_url=api_url,
            timeout=timeout,
            mounts={
                "http://": self._transport,
                "https://": self._transport,
            },
            cookies=self._cookies,
        )
        self._api_url = api_url

    async def post(self, path, error_message: str = "", **kwargs):
        return await self._send_request("POST", path, error_message, **kwargs)

    async def get(self, path, error_message: str = "", **kwargs):
        return await self._send_request("GET", path, error_message, **kwargs)

    async def delete(self, path, error_message: str = "", **kwargs):
        ignore_status_codes = []
        if kwargs.pop("ignore_missing", False):
            ignore_status_codes.append(404)
        return await self._send_request(
            "DELETE",
            path,
            error_message,
            ignore_status_codes=ignore_status_codes,
            **kwargs,
        )

    async def put(self, path, error_message: str = "", **kwargs):
        return await self._send_request("PUT", path, error_message, **kwargs)

    async def close(self):
        await self._session.aclose()

    async def _send_request(self, method, path, error_message: str, **kwargs):
        endpoint = f"api/{path.lstrip('/')}"

        if kwargs.get("timeout") is None:
            kwargs["timeout"] = 60

        self._logger.debug_with(
            "Sending request", method=method, endpoint=endpoint, **kwargs
        )
        headers = copy.deepcopy(self._headers)
        headers.update(kwargs.pop("headers", {}))
        ignore_status_codes = kwargs.pop("ignore_status_codes", [])
        response = await self._session.request(
            method, endpoint, cookies=self._cookies, headers=headers, **kwargs
        )
        self._logger.debug_with("Received response", status_code=response.status_code)
        if response.is_error and response.status_code not in ignore_status_codes:
            log_kwargs = copy.deepcopy(kwargs)
            log_kwargs.update({"method": method, "path": path})
            if response.content:
                try:
                    data = response.json()
                    ctx = data.get("meta", {}).get("ctx")
                    errors = data.get("errors", [])
                except Exception:
                    pass
                else:
                    error_message = f"{error_message}: {str(errors)}"
                    log_kwargs.update({"ctx": ctx, "errors": errors})
            self._logger.warn_with("Request failed", **log_kwargs)

            # reraise with a custom error message to avoid the default one which
            # is not very customizable and friendly
            raise httpx.HTTPStatusError(
                error_message, request=response.request, response=response
            )

        return response


class APIClient:
    def __init__(
        self,
        *,
        endpoint: str = "",
        timeout: int = 60,
        retries: int = 3,
        username: str = "",
        password: str = "",
        access_key: str = "",
    ):
        if password and access_key:
            raise ValueError("Must provide either password or access key")
        if not username:
            username = os.getenv("V3IO_USERNAME")
        if password and not username or access_key and not username:
            raise ValueError(
                "Must provide username when providing password or access key"
            )

        self._logger = v3io.logger.logger.get_or_create_logger(
            level="INFO", name="apic"
        )
        endpoint = v3io.common.helpers.get_endpoint(endpoint, default_scheme="https")
        self._client = _BaseHTTPClient(
            self._logger, endpoint, timeout=timeout, retries=retries
        )

        self._authenticated = False
        if username and access_key:
            self._set_auth(username=username, access_key=access_key)
            self._authenticated = True
        self._username = username
        self._password = password
        self._access_key = access_key

    async def close(self):
        await self._client.close()

    async def login(self, *, username: str = "", password: str = ""):
        """
        Authenticate to the API server using username and password
        """

        username = username or self._username
        password = password or self._password

        # validate both username and password are provided
        if not (username and password):
            raise ValueError("Username and password must be provided")

        await self._login(username, password)

        self._authenticated = True
        self._username = username
        self._password = password
        self._logger.info("Successfully logged in")

    def with_access_key(self, access_key: str):
        """
        Set the access key to be used for authentication
        """
        self._access_key = access_key
        self._set_auth(username=self._username, access_key=access_key)
        return self

    async def wait_for_job_completion(
        self, job_id: str, job_completion_retry_interval: int = 30, timeout: int = 3600
    ) -> None:
        async def _verify_job_in_terminal_state():
            response = await self._client._send_request(
                "GET", f"jobs/{job_id}", "Failed getting job"
            )
            response_body = response.json()
            _job_state = response_body["data"]["attributes"]["state"]
            if _job_state not in JobStates.terminal_states():
                raise RetryUntilSuccessfulInProgressErrorMessage(
                    "Waiting for job completion",
                    variables={
                        "job_id": job_id,
                        "job_state": _job_state,
                    },
                )
            return JobStates(_job_state), response_body["data"]["attributes"]["result"]

        job_state, job_result = await retry_until_successful(
            job_completion_retry_interval,
            timeout,
            self._logger,
            True,
            _verify_job_in_terminal_state,
        )
        if job_state != JobStates.completed:
            error_message = f"Job {job_id} failed with state: {job_state.value}"
            try:
                parsed_result = json.loads(job_result)
                error_message += f", message: {parsed_result['message']}"

                # status is optional
                if "status" in parsed_result:
                    status_code = int(parsed_result["status"])
                    error_message = f", status: {status_code}"
            except Exception:
                pass
            raise RuntimeError(error_message)
        self._logger.info_with("Job completed successfully", job_id=job_id)

    async def create(self, resource_name, attributes, relationships=None, **kwargs):
        """
        Creates a new resource
        :param resource_name: the resource name
        :param attributes: the resource attributes
        :param relationships: the resource relationships
        :param kwargs: additional arguments to pass to the API
        """
        response = await self._client.post(
            inflection.pluralize(resource_name),
            f"Failed to create {resource_name}".strip(),
            json=self.compile_api_request(resource_name, attributes, relationships),
            **kwargs,
        )
        return response.json()

    async def update(
        self, resource_name, resource_id, attributes, relationships=None, **kwargs
    ):
        """
        Updates an existing resource
        :param resource_name: the resource name
        :param resource_id: the resource ID
        :param attributes: the resource attributes
        :param relationships: the resource relationships
        :param kwargs: additional arguments to pass to the request
        """
        return await self._client.put(
            f"{inflection.pluralize(resource_name)}/{resource_id}",
            f"Failed to update {resource_name} {resource_id}".strip(),
            json=self.compile_api_request(resource_name, attributes, relationships),
            **kwargs,
        )

    async def delete(self, resource_name, resource_id, **kwargs):
        """
        Deletes an existing resource
        :param resource_name: the resource name
        :param resource_id: the resource ID to delete
        :param kwargs: additional arguments to pass to the request
        """
        return await self._client.delete(
            f"{inflection.pluralize(resource_name)}/{resource_id}",
            f"Failed to delete {resource_name} {resource_id}".strip(),
            **kwargs,
        )

    async def detail(self, resource_name, resource_id, **kwargs):
        """
        Gets an existing single resource
        :param resource_name: the resource name
        :param resource_id: the resource ID to delete
        :param kwargs: additional arguments to pass to the request
        """
        response = await self._client.get(
            f"{inflection.pluralize(resource_name)}/{resource_id}",
            f"Failed to get {resource_name} {resource_id}".strip(),
            **kwargs,
        )
        return response.json()

    async def list(self, resource_name, **kwargs):
        """
        Lists existing resources
        :param resource_name: the resource name
        :param kwargs: additional arguments to pass to the request
        """
        response = await self._client.get(
            inflection.pluralize(resource_name),
            f"Failed to list {inflection.pluralize(resource_name)}".strip(),
            **kwargs,
        )
        return response.json()

    async def request(self, method, path, **kwargs):
        """
        Executes a raw request
        :param method: the request method
        :param path: the request path
        :param kwargs: additional arguments to pass to the request
        """
        response = await self._client._send_request(
            method, path, "Failed to execute request", **kwargs
        )
        return response.json()

    async def request_job(self, path, **kwargs):
        """
        Executes a raw request and waits for the job to complete
        :param path: the job request path
        :param kwargs: additional arguments to pass to the request
        """
        wait_for_job_completion = kwargs.pop("wait_for_job_completion", True)
        response = await self.request("POST", path, **kwargs)
        job_id = response["data"]["id"]
        if wait_for_job_completion:
            await self.wait_for_job_completion(
                job_id, timeout=kwargs.get("timeout", 360)
            )
        return job_id

    @staticmethod
    def compile_api_request(data_type, attributes, relationships=None):
        return {
            "data": {
                "type": data_type,
                "attributes": attributes,
                "relationships": relationships if relationships else {},
            },
        }

    async def _login(self, username: str, password: str):
        self._logger.debug_with("Authenticating", username=username)
        response = await self._client.post(
            "/sessions",
            "Authentication failed",
            json=self.compile_api_request(
                data_type="session",
                attributes={
                    "username": username,
                    "password": password,
                    "plane": SessionPlanes.control.value,
                },
            ),
        )
        self._set_auth(username=username, session=response.cookies.get("session"))

    def _set_auth(self, username: str, access_key: str = "", session: str = ""):
        if access_key and session:
            raise ValueError("Cannot set both access_key and session")
        self._client._cookies.set(
            "session",
            f"j%3A%7B%22sid%22%3A%20%22{access_key}%22%7D" if access_key else session,
        )

        if access_key:
            encoded_auth = f"{username}:{access_key}"
            base64_encoded_auth = base64.b64encode(encoded_auth.encode("utf-8")).decode(
                "utf-8"
            )
            self._client._headers["Authorization"] = f"Basic {base64_encoded_auth}"
