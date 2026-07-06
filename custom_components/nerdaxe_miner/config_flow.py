"""Config flow for the NerdAxe Miner integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import MinerApiClient, MinerApiError, normalize_host
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
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)
from .normalizer import find_stable_device_id


def _options_schema(defaults: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(
                CONF_SCAN_INTERVAL,
                default=defaults.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            ): vol.All(
                vol.Coerce(int),
                vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL),
            ),
            vol.Required(
                CONF_HISTORY_ENABLED,
                default=defaults.get(CONF_HISTORY_ENABLED, DEFAULT_HISTORY_ENABLED),
            ): bool,
            vol.Required(
                CONF_HISTORY_MAX_MB,
                default=defaults.get(CONF_HISTORY_MAX_MB, DEFAULT_HISTORY_MAX_MB),
            ): vol.All(vol.Coerce(int), vol.Range(min=1)),
            vol.Required(
                CONF_HISTORY_RAW_KEEP_DAYS,
                default=defaults.get(
                    CONF_HISTORY_RAW_KEEP_DAYS,
                    DEFAULT_HISTORY_RAW_KEEP_DAYS,
                ),
            ): vol.All(vol.Coerce(int), vol.Range(min=1)),
            vol.Required(
                CONF_HISTORY_STORE_RAW_PAYLOAD,
                default=defaults.get(
                    CONF_HISTORY_STORE_RAW_PAYLOAD,
                    DEFAULT_HISTORY_STORE_RAW_PAYLOAD,
                ),
            ): bool,
        }
    )


def _config_schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    defaults = defaults or {}
    option_schema = _options_schema(defaults).schema
    return vol.Schema(
        {
            vol.Required(CONF_HOST, default=defaults.get(CONF_HOST, "")): str,
            **option_schema,
        }
    )


def _extract_options(user_input: dict[str, Any]) -> dict[str, Any]:
    return {
        CONF_SCAN_INTERVAL: user_input[CONF_SCAN_INTERVAL],
        CONF_HISTORY_ENABLED: user_input[CONF_HISTORY_ENABLED],
        CONF_HISTORY_MAX_MB: user_input[CONF_HISTORY_MAX_MB],
        CONF_HISTORY_RAW_KEEP_DAYS: user_input[CONF_HISTORY_RAW_KEEP_DAYS],
        CONF_HISTORY_STORE_RAW_PAYLOAD: user_input[CONF_HISTORY_STORE_RAW_PAYLOAD],
    }


class NerdAxeMinerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for NerdAxe Miner."""

    VERSION = 1
    MINOR_VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""

        return NerdAxeMinerOptionsFlow()

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> Any:
        """Handle the initial step."""

        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                host = normalize_host(user_input[CONF_HOST])
            except ValueError:
                errors[CONF_HOST] = "invalid_host"
            else:
                if self._host_is_configured(host):
                    return self.async_abort(reason="already_configured")

                session = async_get_clientsession(self.hass)
                client = MinerApiClient(host, session)
                try:
                    payload = await client.async_get_info()
                except MinerApiError:
                    errors["base"] = "cannot_connect"
                except Exception:
                    errors["base"] = "unknown"
                else:
                    stable_id = find_stable_device_id(payload)
                    if stable_id:
                        await self.async_set_unique_id(stable_id)
                        self._abort_if_unique_id_configured(updates={CONF_HOST: host})

                    title = str(payload.get("hostname") or host)
                    return self.async_create_entry(
                        title=title,
                        data={CONF_HOST: host},
                        options=_extract_options(user_input),
                    )

        return self.async_show_form(
            step_id="user",
            data_schema=_config_schema(user_input),
            errors=errors,
        )

    def _host_is_configured(self, host: str) -> bool:
        return any(
            normalize_host(entry.data.get(CONF_HOST, "")) == host
            for entry in self._async_current_entries()
            if entry.data.get(CONF_HOST)
        )


class NerdAxeMinerOptionsFlow(config_entries.OptionsFlowWithReload):
    """Handle NerdAxe Miner options."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> Any:
        """Manage options."""

        if user_input is not None:
            return self.async_create_entry(data=user_input)

        defaults = {
            CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
            CONF_HISTORY_ENABLED: DEFAULT_HISTORY_ENABLED,
            CONF_HISTORY_MAX_MB: DEFAULT_HISTORY_MAX_MB,
            CONF_HISTORY_RAW_KEEP_DAYS: DEFAULT_HISTORY_RAW_KEEP_DAYS,
            CONF_HISTORY_STORE_RAW_PAYLOAD: DEFAULT_HISTORY_STORE_RAW_PAYLOAD,
            **dict(self.config_entry.options),
        }

        return self.async_show_form(
            step_id="init",
            data_schema=_options_schema(defaults),
        )
