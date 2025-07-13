import abc
import logging

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)


class APIError(Exception): ...


class BaseAPIClient(abc.ABC):
    BASE_URL: str

    def __init__(self, api_key: str, *, timeout: int = 10):
        self._api_key = api_key
        self._timeout = timeout
        self._client = httpx.AsyncClient(base_url=self.BASE_URL, timeout=timeout)

    @retry(
        retry=retry_if_exception_type(httpx.HTTPStatusError),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def _get(self, path: str, params: dict | None = None) -> dict:
        resp = await self._client.get(path, params=params)
        try:
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            logger.error(
                "HTTP error",
                extra={"status": e.response.status_code, "url": str(e.request.url)},
            )
            raise APIError from e
        return resp.json()

    async def aclose(self):
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        await self.aclose()
