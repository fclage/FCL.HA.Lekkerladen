"""Lekkerladen Home Assistant integration."""

from __future__ import annotations

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import LekkerladenApi
from .const import CONF_TOKEN
from .coordinator import LekkerladenConfigEntry, LekkerladenCoordinator

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: LekkerladenConfigEntry) -> bool:
    """Set up Lekkerladen from a config entry."""
    api = LekkerladenApi(
        async_get_clientsession(hass),
        token=entry.data.get(CONF_TOKEN),
    )
    coordinator = LekkerladenCoordinator(hass, api, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: LekkerladenConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
