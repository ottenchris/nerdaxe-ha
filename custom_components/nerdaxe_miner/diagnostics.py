"""Diagnostics support for NerdAxe Miner."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant

from .const import DOMAIN

TO_REDACT = {CONF_HOST, "rawPayload", "upstreamUrl"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""

    coordinator = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    last_sample = None
    history = None

    if coordinator is not None:
        if coordinator.data is not None:
            last_sample = coordinator.data.as_history_dict(include_raw_payload=False)
        if coordinator.history_store is not None:
            history = {
                "root_dir": str(coordinator.history_store.root_dir),
                "max_bytes": coordinator.history_store.max_bytes,
                "raw_keep_days": coordinator.history_store.raw_keep_days,
                "store_raw_payload": coordinator.history_store.store_raw_payload,
            }

    return {
        "entry": {
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "options": async_redact_data(dict(entry.options), TO_REDACT),
        },
        "last_sample": async_redact_data(last_sample or {}, TO_REDACT),
        "history": async_redact_data(history or {}, TO_REDACT),
    }
