"""Aiohttp API client for AxeOS/ESP-Miner compatible miners."""

from __future__ import annotations

import asyncio
from typing import Any
from urllib.parse import urlsplit

import aiohttp

from .const import (
    DEFAULT_TIMEOUT_SECONDS,
    FAN_SPEED_MAX,
    FAN_SPEED_MIN,
    INFO_PATH,
    PID_TARGET_TEMP_MAX,
    PID_TARGET_TEMP_MIN,
    RESTART_PATH,
    SYSTEM_PATH,
)


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


def build_api_url(host: str, path: str) -> str:
    """Build a miner API endpoint URL for a host and absolute path."""

    if not path.startswith("/"):
        raise ValueError("path must be absolute")
    return f"http://{normalize_host(host)}{path}"


def build_info_url(host: str) -> str:
    """Build the miner info endpoint URL for a host."""

    return build_api_url(host, INFO_PATH)


def _validate_int_range(value: int, *, name: str, minimum: int, maximum: int) -> None:
    """Validate an integer value before it is sent to the miner."""

    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    if value < minimum or value > maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")


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

    @property
    def restart_url(self) -> str:
        """Return the system restart endpoint URL."""

        return self._build_url(RESTART_PATH)

    async def async_get_info(self) -> dict[str, Any]:
        """Fetch and parse miner system info."""

        payload = await self._async_request("GET", INFO_PATH, expect_json=True)
        if not isinstance(payload, dict):
            raise MinerApiError(
                "Miner returned a non-object JSON payload",
                url=self.info_url,
            )

        return payload

    async def async_restart(self) -> None:
        """Restart the miner through the documented AxeOS endpoint."""

        await self._async_request("POST", RESTART_PATH, expect_json=False)

    async def async_set_fan_control_mode(self, auto: bool) -> None:
        """Set the miner fan control mode."""

        if not isinstance(auto, bool):
            raise ValueError("auto must be a boolean")
        await self._async_patch_system_settings({"autofanspeed": 1 if auto else 0})

    async def async_set_manual_fan_speed(self, percent: int) -> None:
        """Set the manual fan speed percentage."""

        _validate_int_range(
            percent,
            name="manual fan speed",
            minimum=FAN_SPEED_MIN,
            maximum=FAN_SPEED_MAX,
        )
        await self._async_patch_system_settings({"manualFanSpeed": percent})

    async def async_set_pid_target_temp(self, celsius: int) -> None:
        """Set the PID target temperature in degrees Celsius."""

        _validate_int_range(
            celsius,
            name="PID target temperature",
            minimum=PID_TARGET_TEMP_MIN,
            maximum=PID_TARGET_TEMP_MAX,
        )
        await self._async_patch_system_settings({"temptarget": celsius})

    async def _async_patch_system_settings(self, payload: dict[str, Any]) -> None:
        """Patch a narrow set of system settings."""

        await self._async_request(
            "PATCH",
            SYSTEM_PATH,
            expect_json=False,
            json_body=payload,
        )

    def _build_url(self, path: str) -> str:
        """Build a URL for a miner API path."""

        return build_api_url(self.host, path)

    async def _async_request(
        self,
        method: str,
        path: str,
        *,
        expect_json: bool,
        json_body: dict[str, Any] | None = None,
    ) -> Any:
        """Run one HTTP request against the miner API."""

        url = self._build_url(path)
        request_kwargs: dict[str, Any] = {
            "headers": {"Accept": "application/json"},
            "timeout": self._timeout,
        }
        if json_body is not None:
            request_kwargs["json"] = json_body

        try:
            async with self._session.request(
                method,
                url,
                **request_kwargs,
            ) as response:
                if response.status >= 400:
                    body = (await response.text()).strip()[:300]
                    raise MinerApiError(
                        f"Miner returned HTTP {response.status}",
                        url=url,
                        status=response.status,
                        body_preview=body or None,
                    )

                if not expect_json:
                    return None

                try:
                    return await response.json(content_type=None)
                except Exception as err:
                    body = (await response.text()).strip()[:300]
                    raise MinerApiError(
                        "Miner returned invalid JSON",
                        url=url,
                        body_preview=body or None,
                    ) from err
        except asyncio.TimeoutError as err:
            raise MinerApiError(
                "Timed out while contacting miner",
                url=url,
            ) from err
        except aiohttp.ClientError as err:
            raise MinerApiError(str(err), url=url) from err
