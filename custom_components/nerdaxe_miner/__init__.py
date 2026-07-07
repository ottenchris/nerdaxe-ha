"""The NerdAxe Miner integration."""

from __future__ import annotations

from .const import DOMAIN


async def async_setup_entry(hass, entry) -> bool:
    """Set up NerdAxe Miner from a config entry."""

    from homeassistant.const import CONF_HOST, Platform
    from homeassistant.helpers.aiohttp_client import async_get_clientsession

    from .api import MinerApiClient
    from .coordinator import NerdAxeMinerCoordinator

    platforms = (
        Platform.SENSOR,
        Platform.BINARY_SENSOR,
        Platform.BUTTON,
        Platform.SELECT,
        Platform.NUMBER,
    )
    session = async_get_clientsession(hass)
    client = MinerApiClient(entry.data[CONF_HOST], session)
    coordinator = NerdAxeMinerCoordinator(hass, entry, client)

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, platforms)
    return True


async def async_unload_entry(hass, entry) -> bool:
    """Unload a config entry."""

    from homeassistant.const import Platform

    platforms = (
        Platform.SENSOR,
        Platform.BINARY_SENSOR,
        Platform.BUTTON,
        Platform.SELECT,
        Platform.NUMBER,
    )
    unload_ok = await hass.config_entries.async_unload_platforms(entry, platforms)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
