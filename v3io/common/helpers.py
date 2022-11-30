# Copyright 2019 Iguazio
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import time
import traceback
import os
import string
import random
import asyncio


def url_join(base, *parts):
    result = base

    if result[0] != '/':
        result = '/' + base

    for part in parts:
        if part[0] != '/':
            result += '/' + part
        else:
            result += part

    return result


def create_linear_backoff(base=2, coefficient=2, stop_value=120):
    """
    Create a generator of linear backoff. Check out usage example in test_helpers.py
    """
    x = 0
    comparison = min if coefficient >= 0 else max

    while True:
        next_value = comparison(base + x * coefficient, stop_value)
        yield next_value
        x += 1


async def retry_until_successful(
        backoff: int, timeout: int, logger, verbose: bool, function, *args, **kwargs
):
    """
    Runs function with given *args and **kwargs.
    Tries to run it until success or timeout reached (timeout is optional)
    :param backoff: can either be a:
            - number (int / float) that will be used as interval.
            - generator of waiting intervals. (support next())
    :param timeout: pass None if timeout is not wanted, number of seconds if it is
    :param logger: a logger so we can log the failures
    :param verbose: whether to log the failure on each retry
    :param function: function to run
    :param args: functions args
    :param kwargs: functions kwargs
    :return: function result
    """
    start_time = time.time()
    last_traceback = None
    last_exception = None
    function_name = function.__name__

    # Check if backoff is just a simple interval
    if isinstance(backoff, int) or isinstance(backoff, float):
        backoff = create_linear_backoff(base=backoff, coefficient=0)

    # If deadline was not provided or deadline not reached
    while timeout is None or time.time() < start_time + timeout:
        next_interval = next(backoff)
        try:
            if asyncio.iscoroutinefunction(function):
                results = await function(*args, **kwargs)
            else:
                results = function(*args, **kwargs)
            return results

        except Exception as exc:
            if logger is not None and verbose:
                log_kwargs = {
                    "next_try_in": next_interval,
                    "function_name": function_name,
                }
                if isinstance(exc, RetryUntilSuccessfulInProgressErrorMessage):
                    log_kwargs.update(exc.variables)

                logger.debug_with(
                    str(exc),
                    **log_kwargs,
                )

            last_exception = exc
            last_traceback = traceback.format_exc()

            # If next interval is within allowed time period - wait on interval, abort otherwise
            if timeout is None or time.time() + next_interval < start_time + timeout:
                await asyncio.sleep(next_interval)
            else:
                break

    if logger is not None:
        logger.warn_with(
            "Operation did not complete on time",
            function_name=function_name,
            timeout=timeout,
            exc=str(last_exception),
            tb=last_traceback,
        )

    raise Exception(
        f"failed to execute command by the given deadline."
        f" last_exception: {last_exception},"
        f" function_name: {function.__name__},"
        f" timeout: {timeout}"
    )


def random_string(length: int) -> str:
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for _ in range(length))


def get_endpoint(endpoint, default_scheme='http'):
    if endpoint is None:
        endpoint = os.environ.get('V3IO_API')

        if endpoint is None:
            raise RuntimeError('Endpoints must be passed to context or specified in V3IO_API')

    if not endpoint.startswith('http://') and not endpoint.startswith('https://'):
        endpoint = f'{default_scheme}://{endpoint}'

    return endpoint.rstrip('/')
