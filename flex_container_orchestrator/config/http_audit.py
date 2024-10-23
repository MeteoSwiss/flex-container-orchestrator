"""
Note: This script from mchpy (MeteoSwiss Blueprint) was added here because I couldn't install mchpy from outside of the MeteoSwiss network.

Instrumentation of web applications to include the request_id in all responses
and make it available to other services (e.g. logging)
"""

# noinspection PyPackageRequirements
import contextvars
import logging
import uuid
from typing import Callable

X_REQUEST_ID = "X-REQUEST-ID"
request_id = contextvars.ContextVar("request_id", default="")

logger = logging.getLogger(__name__)


def get_request_id() -> str:
    """
    Get the request_id valid for the entire request.
    """
    return request_id.get()


def extract_request_id_from(extract_request_fn: Callable[[str], str | None]) -> str:
    """
    Extracts the request id from the incoming request by using the given function

    :param extract_request_fn: request id extract function, accepting as argument the request id name.
        Must return the request id string value, or None
    """
    rid = extract_request_fn(X_REQUEST_ID) or _generate_request_id()
    request_id.set(rid)

    return rid


def _generate_request_id() -> str:
    rid = str(uuid.uuid4())
    logger.debug("Generated new request_id %s", rid)

    return rid
