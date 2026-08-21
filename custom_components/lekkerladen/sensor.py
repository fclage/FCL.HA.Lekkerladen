"""Lekkerladen sensors: energy, ERE rate, estimated payout, charger sessions."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import CURRENCY_EURO, UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import AMSTERDAM_TZ, ATTRIBUTION, CONF_USER_ID
from .coordinator import LekkerladenConfigEntry, LekkerladenCoordinator
from .entity import account_device, charger_device
from .models import match_charger_sessions, parse_iso


@dataclass(frozen=True, kw_only=True)
class LekkerladenSensorDescription(SensorEntityDescription):
    value_fn: Callable[[dict[str, Any]], Any]
    attr_fn: Callable[[dict[str, Any]], dict[str, Any]] | None = None


def _computed(data: dict[str, Any]) -> dict[str, Any]:
    return data.get("computed") or {}


def _profile(data: dict[str, Any]) -> dict[str, Any]:
    return data.get("profile") or {}


def _first_account(data: dict[str, Any]) -> dict[str, Any]:
    accounts = data.get("accounts") or []
    return accounts[0] if accounts else {}


ACCOUNT_SENSORS: tuple[LekkerladenSensorDescription, ...] = (
    LekkerladenSensorDescription(
        key="month_energy",
        translation_key="month_energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=2,
        icon="mdi:lightning-bolt",
        value_fn=lambda d: _computed(d).get("month_kwh"),
    ),
    LekkerladenSensorDescription(
        key="ytd_energy",
        translation_key="ytd_energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=2,
        icon="mdi:lightning-bolt-outline",
        value_fn=lambda d: _computed(d).get("ytd_kwh"),
    ),
    LekkerladenSensorDescription(
        key="month_sessions",
        translation_key="month_sessions",
        state_class=SensorStateClass.TOTAL,
        icon="mdi:counter",
        value_fn=lambda d: _computed(d).get("month_sessions"),
    ),
    LekkerladenSensorDescription(
        key="ytd_sessions",
        translation_key="ytd_sessions",
        state_class=SensorStateClass.TOTAL,
        icon="mdi:counter",
        value_fn=lambda d: _computed(d).get("ytd_sessions"),
    ),
    LekkerladenSensorDescription(
        key="ere_price",
        translation_key="ere_price",
        native_unit_of_measurement=CURRENCY_EURO,
        device_class=SensorDeviceClass.MONETARY,
        suggested_display_precision=3,
        icon="mdi:certificate",
        value_fn=lambda d: _computed(d).get("ere_price"),
        attr_fn=lambda d: {"rate_date": _computed(d).get("ere_date")},
    ),
    LekkerladenSensorDescription(
        key="ere_per_kwh",
        translation_key="ere_per_kwh",
        native_unit_of_measurement=f"{CURRENCY_EURO}/{UnitOfEnergy.KILO_WATT_HOUR}",
        suggested_display_precision=3,
        icon="mdi:currency-eur",
        value_fn=lambda d: _computed(d).get("ere_per_kwh"),
    ),
    LekkerladenSensorDescription(
        key="net_per_kwh",
        translation_key="net_per_kwh",
        native_unit_of_measurement=f"{CURRENCY_EURO}/{UnitOfEnergy.KILO_WATT_HOUR}",
        suggested_display_precision=4,
        icon="mdi:currency-eur",
        value_fn=lambda d: _computed(d).get("net_eur_per_kwh"),
        attr_fn=lambda d: {
            "commission_rate": _computed(d).get("commission_rate"),
            "note": "Gross ERE €/kWh after Lekkerladen commission",
        },
    ),
    LekkerladenSensorDescription(
        key="month_payout",
        translation_key="month_payout",
        native_unit_of_measurement=CURRENCY_EURO,
        device_class=SensorDeviceClass.MONETARY,
        suggested_display_precision=2,
        icon="mdi:cash",
        value_fn=lambda d: _computed(d).get("month_eur"),
    ),
    LekkerladenSensorDescription(
        key="ytd_payout",
        translation_key="ytd_payout",
        native_unit_of_measurement=CURRENCY_EURO,
        device_class=SensorDeviceClass.MONETARY,
        suggested_display_precision=2,
        icon="mdi:cash",
        value_fn=lambda d: _computed(d).get("ytd_eur"),
    ),
    LekkerladenSensorDescription(
        key="payout_frequency",
        translation_key="payout_frequency",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:calendar-month",
        value_fn=lambda d: _profile(d).get("payoutFrequency"),
    ),
    LekkerladenSensorDescription(
        key="partner",
        translation_key="partner",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:handshake",
        value_fn=lambda d: _profile(d).get("partner"),
    ),
    LekkerladenSensorDescription(
        key="account_last_fetched",
        translation_key="account_last_fetched",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:cloud-sync",
        value_fn=lambda d: parse_iso(_first_account(d).get("lastFetchedDate")),
    ),
    LekkerladenSensorDescription(
        key="session_expires",
        translation_key="session_expires",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:timer-lock",
        value_fn=lambda d: _computed(d).get("session_expires"),
    ),
    LekkerladenSensorDescription(
        key="contract_expires",
        translation_key="contract_expires",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:file-sign",
        value_fn=lambda d: parse_iso((_computed(d).get("mandate") or {}).get("consentExpiresAt")),
    ),
)


@dataclass(frozen=True, kw_only=True)
class ChargerSensorDescription(SensorEntityDescription):
    value_fn: Callable[[dict[str, Any], list[dict[str, Any]]], Any]


CHARGER_SENSORS: tuple[ChargerSensorDescription, ...] = (
    ChargerSensorDescription(
        key="latest_session_energy",
        translation_key="latest_session_energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=3,
        icon="mdi:ev-station",
        value_fn=lambda charger, sessions: (
            sessions[0].get("energyDeliveredKwh") if sessions else None
        ),
    ),
    ChargerSensorDescription(
        key="latest_session_start",
        translation_key="latest_session_start",
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:clock-start",
        value_fn=lambda charger, sessions: (
            parse_iso(sessions[0].get("startTime")) if sessions else None
        ),
    ),
    ChargerSensorDescription(
        key="latest_session_end",
        translation_key="latest_session_end",
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:clock-end",
        value_fn=lambda charger, sessions: (
            parse_iso(sessions[0].get("endTime")) if sessions else None
        ),
    ),
    ChargerSensorDescription(
        key="serial_number",
        translation_key="serial_number",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:barcode",
        value_fn=lambda charger, sessions: charger.get("serialNumber"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LekkerladenConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    user_id = entry.data.get(CONF_USER_ID) or entry.unique_id or entry.entry_id
    entities: list[SensorEntity] = [
        LekkerladenAccountSensor(coordinator, entry, user_id, description)
        for description in ACCOUNT_SENSORS
    ]
    for charger in coordinator.data.get("chargers") or []:
        charger_id = charger.get("id")
        if not charger_id:
            continue
        for description in CHARGER_SENSORS:
            entities.append(
                LekkerladenChargerSensor(
                    coordinator, entry, user_id, charger_id, description
                )
            )
    async_add_entities(entities)


class LekkerladenAccountSensor(
    CoordinatorEntity[LekkerladenCoordinator], SensorEntity
):
    _attr_has_entity_name = True
    _attr_attribution = ATTRIBUTION
    entity_description: LekkerladenSensorDescription

    def __init__(
        self,
        coordinator: LekkerladenCoordinator,
        entry: LekkerladenConfigEntry,
        user_id: str,
        description: LekkerladenSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._user_id = str(user_id)
        self._attr_unique_id = f"{self._user_id}_{description.key}"
        self._attr_device_info = account_device(self._user_id, coordinator.data or {})

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self.coordinator.data or {})

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if not self.entity_description.attr_fn:
            return None
        return self.entity_description.attr_fn(self.coordinator.data or {})

    @property
    def last_reset(self) -> datetime | None:
        if self.entity_description.key == "ytd_energy":
            year = _computed(self.coordinator.data or {}).get("year")
            if year:
                return datetime(int(year), 1, 1, tzinfo=ZoneInfo(AMSTERDAM_TZ))
        if self.entity_description.key in {"month_energy", "month_sessions"}:
            ym = _computed(self.coordinator.data or {}).get("year_month")
            if isinstance(ym, str) and len(ym) == 7:
                year, month = ym.split("-")
                return datetime(int(year), int(month), 1, tzinfo=ZoneInfo(AMSTERDAM_TZ))
        if self.entity_description.key == "ytd_sessions":
            year = _computed(self.coordinator.data or {}).get("year")
            if year:
                return datetime(int(year), 1, 1, tzinfo=ZoneInfo(AMSTERDAM_TZ))
        return None


class LekkerladenChargerSensor(
    CoordinatorEntity[LekkerladenCoordinator], SensorEntity
):
    _attr_has_entity_name = True
    _attr_attribution = ATTRIBUTION
    entity_description: ChargerSensorDescription

    def __init__(
        self,
        coordinator: LekkerladenCoordinator,
        entry: LekkerladenConfigEntry,
        user_id: str,
        charger_id: str,
        description: ChargerSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._charger_id = charger_id
        self._attr_unique_id = f"{charger_id}_{description.key}"
        charger = self._charger() or {"id": charger_id}
        self._attr_device_info = charger_device(user_id, charger)

    def _charger(self) -> dict[str, Any] | None:
        for charger in self.coordinator.data.get("chargers") or []:
            if charger.get("id") == self._charger_id:
                return charger
        return None

    def _sessions(self) -> list[dict[str, Any]]:
        charger = self._charger()
        if not charger:
            return []
        return match_charger_sessions(charger, self.coordinator.data.get("sessions") or [])

    @property
    def native_value(self) -> Any:
        charger = self._charger() or {}
        return self.entity_description.value_fn(charger, self._sessions())

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if self.entity_description.key != "latest_session_energy":
            return None
        sessions = self._sessions()
        if not sessions:
            return None
        latest = sessions[0]
        return {
            "session_id": latest.get("sessionId"),
            "certified": latest.get("isCertified"),
            "complete": latest.get("isComplete"),
            "provider": latest.get("providerId"),
        }
