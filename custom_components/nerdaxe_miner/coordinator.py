"""Coordinator for NerdAxe miner polling and history recording."""

from __future__ import annotations

from datetime import timedelta
import logging
from pathlib import Path
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import MinerApiClient
from .const import (
    CONF_HISTORY_ENABLED,
    CONF_HISTORY_MAX_MB,
    CONF_HISTORY_RAW_KEEP_DAYS,
    CONF_HISTORY_STORE_RAW_PAYLOAD,
    CONF_SCAN_INTERVAL,
    DEFAULT_HISTORY_ENABLED,
    DEFAULT_HISTORY_MAX_MB,
    DEFAULT_HISTORY_RAW_KEEP_DAYS,
    DEFAULT_HISTORY_STORE_RAW_PAYLOAD,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    RECORDER_DIR_NAME,
)
from .history_store import NerdAxeHistoryStore
from .models import MinerSample
from .normalizer import normalize_miner_payload, slugify_identifier

_LOGGER = logging.getLogger(__name__)


class NerdAxeMinerCoordinator(DataUpdateCoordinator[MinerSample]):
    """Poll the miner once and fan out the result to all entities."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        api: MinerApiClient,
    ) -> None:
        """Initialize the coordinator."""

        self.entry = entry
        self.api = api
        self._history_store = self._create_history_store(hass, entry)
        self._device_identifier = entry.unique_id or entry.entry_id

        scan_interval = int(entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry.entry_id}",
            config_entry=entry,
            update_interval=timedelta(seconds=scan_interval),
            always_update=True,
        )

    @property
    def entity_unique_prefix(self) -> str:
        """Return the stable prefix used for entity unique IDs."""

        return self.entry.unique_id or self.entry.entry_id

    @property
    def device_info(self) -> dict[str, Any]:
        """Return Home Assistant device registry data."""

        data = self.data
        name = data.hostname if data and data.hostname else self.entry.data[CONF_HOST]
        device_info: dict[str, Any] = {
            "identifiers": {(DOMAIN, self._device_identifier)},
            "manufacturer": "NerdAxe",
            "model": "AxeOS / ESP-Miner compatible miner",
            "name": name,
            "configuration_url": f"http://{self.api.host}",
        }
        if data and data.firmware_version:
            device_info["sw_version"] = data.firmware_version
        return device_info

    @property
    def history_store(self) -> NerdAxeHistoryStore | None:
        """Return the history store if enabled."""

        return self._history_store

    async def _async_update_data(self) -> MinerSample:
        try:
            payload = await self.api.async_get_info()
            sample = normalize_miner_payload(payload)
        except Exception as err:
            await self._record_fetch_error(err)
            raise UpdateFailed(str(err)) from err

        await self._record_sample(sample)
        return sample

    def _create_history_store(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
    ) -> NerdAxeHistoryStore | None:
        if not bool(entry.options.get(CONF_HISTORY_ENABLED, DEFAULT_HISTORY_ENABLED)):
            return None

        max_mb = int(entry.options.get(CONF_HISTORY_MAX_MB, DEFAULT_HISTORY_MAX_MB))
        raw_keep_days = int(
            entry.options.get(CONF_HISTORY_RAW_KEEP_DAYS, DEFAULT_HISTORY_RAW_KEEP_DAYS)
        )
        store_raw_payload = bool(
            entry.options.get(
                CONF_HISTORY_STORE_RAW_PAYLOAD,
                DEFAULT_HISTORY_STORE_RAW_PAYLOAD,
            )
        )
        device_dir = slugify_identifier(entry.unique_id or entry.entry_id)
        root_dir = Path(hass.config.path(RECORDER_DIR_NAME, device_dir))

        return NerdAxeHistoryStore(
            root_dir,
            max_bytes=max_mb * 1024 * 1024,
            raw_keep_days=raw_keep_days,
            store_raw_payload=store_raw_payload,
            executor_job=hass.async_add_executor_job,
        )

    async def _record_sample(self, sample: MinerSample) -> None:
        if self._history_store is None:
            return
        try:
            await self._history_store.async_append_sample(sample)
        except Exception:
            _LOGGER.exception("Failed to append NerdAxe history sample")

    async def _record_fetch_error(self, error: Exception) -> None:
        if self._history_store is None:
            return
        try:
            await self._history_store.async_append_fetch_error("coordinator", error)
        except Exception:
            _LOGGER.exception("Failed to append NerdAxe fetch error event")
