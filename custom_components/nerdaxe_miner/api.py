"""Aiohttp API client for AxeOS/ESP-Miner compatible miners."""

from __future__ import annotations

import asyncio
from typing import Any
from urllib.parse import urlsplit

import aiohttp

from .const import DEFAULT_TIMEOUT_SECONDS, INFO_PATH


class MinerApiError(Exception):
    """Raised when the miner API cannot be read."""

    def __init__(
        self,
        message: str,
        *,
        url: str,
        status: int | None = None,
        body_preview: str | None = None,
    ) -> None:
        super().__init__(message)
        self.url = url
        self.status = status
        self.body_preview = body_preview


def normalize_host(host: str) -> str:
    """Normalize user-entered host/IP input to host[:port]."""

    value = str(host).strip()
    if not value:
        raise ValueError("host is required")

    if "://" in value:
        parsed = urlsplit(value)
        value = parsed.netloc or parsed.path
    else:
        value = value.split("/", 1)[0]

    value = value.strip().strip("/")
    if not value:
        raise ValueError("host is required")
    return value.lower()


def build_info_url(host: str) -> str:
    """Build the miner info endpoint URL for a host."""

    return f"http://{normalize_host(host)}{INFO_PATH}"


class MinerApiClient:
    """Small aiohttp client for the local miner REST API."""

    def __init__(
        self,
        host: str,
        session: aiohttp.ClientSession,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self.host = normalize_host(host)
        self._session = session
        self._timeout = aiohttp.ClientTimeout(total=timeout_seconds)

    @property
    def info_url(self) -> str:
        """Return the system info endpoint URL."""

        return build_info_url(self.host)

    async def async_get_info(self) -> dict[str, Any]:
        """Fetch and parse miner system info."""

        try:
            async with self._session.get(
                self.info_url,
                headers={"Accept": "application/json"},
                timeout=self._timeout,
            ) as response:
                if response.status >= 400:
                    body = (await response.text()).strip()[:300]
                    raise MinerApiError(
                        f"Miner returned HTTP {response.status}",
                        url=self.info_url,
                        status=response.status,
                        body_preview=body or None,
                    )

                try:
                    payload = await response.json(content_type=None)
                except Exception as err:
                    body = (await response.text()).strip()[:300]
                    raise MinerApiError(
                        "Miner returned invalid JSON",
                        url=self.info_url,
                        body_preview=body or None,
                    ) from err
        except asyncio.TimeoutError as err:
            raise MinerApiError(
                "Timed out while fetching miner data",
                url=self.info_url,
            ) from err
        except aiohttp.ClientError as err:
            raise MinerApiError(str(err), url=self.info_url) from err

        if not isinstance(payload, dict):
            raise MinerApiError(
                "Miner returned a non-object JSON payload",
                url=self.info_url,
            )

        return payload
