"""Poll Lekkerladen and cache dashboard data."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import LekkerladenApi
from .const import CONF_EXPIRES_AT, CONF_TOKEN, DEFAULT_SCAN_INTERVAL, DOMAIN
from .exceptions import LekkerladenAuthError, LekkerladenCannotConnect
from .models import (
    contract_mandate,
    current_year,
    current_year_month,
    estimate_eur,
    month_energy_kwh,
    month_session_count,
    net_eur_per_kwh,
    parse_iso,
    year_energy_kwh,
    year_session_count,
)

_LOGGER = logging.getLogger(__name__)

type LekkerladenConfigEntry = ConfigEntry["LekkerladenCoordinator"]


class LekkerladenCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Refresh chargers, sessions, ERE rate, and contract."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: LekkerladenApi,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=DEFAULT_SCAN_INTERVAL,
            config_entry=entry,
        )
        self.api = api
        self.entry = entry

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            raw = await self.api.fetch_dashboard()
        except LekkerladenAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except LekkerladenCannotConnect as err:
            raise UpdateFailed(str(err)) from err

        session_block = raw.get("auth_session") or {}
        session = session_block.get("session") or {}
        token = session.get("token") or self.api.token
        expires_at = session.get("expiresAt")
        if token and token != self.entry.data.get(CONF_TOKEN):
            self.hass.config_entries.async_update_entry(
                self.entry,
                data={
                    **self.entry.data,
                    CONF_TOKEN: token,
                    CONF_EXPIRES_AT: expires_at,
                },
            )
            self.api.set_token(token)
        elif expires_at and expires_at != self.entry.data.get(CONF_EXPIRES_AT):
            self.hass.config_entries.async_update_entry(
                self.entry,
                data={**self.entry.data, CONF_EXPIRES_AT: expires_at},
            )

        months = raw.get("monthly") or []
        ere_rate = raw.get("ere_rate") or {}
        mandate = contract_mandate(raw.get("contract"))
        commission = mandate.get("commissionRate")
        try:
            commission_f = float(commission) if commission is not None else None
        except (TypeError, ValueError):
            commission_f = None
        net_rate = net_eur_per_kwh(ere_rate, commission_f)
        year = current_year()
        year_month = current_year_month()
        month_kwh = month_energy_kwh(months, year_month)
        ytd_kwh = year_energy_kwh(months, year)

        return {
            **raw,
            "computed": {
                "year": year,
                "year_month": year_month,
                "month_kwh": month_kwh,
                "month_sessions": month_session_count(months, year_month),
                "ytd_kwh": ytd_kwh,
                "ytd_sessions": year_session_count(months, year),
                "ere_price": ere_rate.get("erePrice"),
                "ere_per_kwh": ere_rate.get("perKwh"),
                "ere_date": ere_rate.get("date"),
                "commission_rate": commission_f,
                "net_eur_per_kwh": net_rate,
                "month_eur": estimate_eur(month_kwh, net_rate),
                "ytd_eur": estimate_eur(ytd_kwh, net_rate),
                "mandate": mandate,
                "session_expires": parse_iso(expires_at),
            },
        }
