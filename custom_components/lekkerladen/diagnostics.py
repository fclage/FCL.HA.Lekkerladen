"""Diagnostics with secrets stripped."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_EMAIL
from homeassistant.core import HomeAssistant

from .const import CONF_TOKEN
from .coordinator import LekkerladenConfigEntry

TO_REDACT = {
    CONF_TOKEN,
    CONF_EMAIL,
    "email",
    "ean",
    "eanCode",
    "phoneNumber",
    "street",
    "houseNumber",
    "zipcode",
    "token",
    "ipAddress",
    "userAgent",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: LekkerladenConfigEntry
) -> dict[str, Any]:
    coordinator = entry.runtime_data
    return {
        "entry": async_redact_data(dict(entry.data), TO_REDACT),
        "data": async_redact_data(coordinator.data or {}, TO_REDACT),
    }
