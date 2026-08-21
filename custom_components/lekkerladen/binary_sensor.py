"""Lekkerladen binary sensors: contract, account token, charger MID."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, CONF_USER_ID
from .coordinator import LekkerladenConfigEntry, LekkerladenCoordinator
from .entity import account_device, charger_device


@dataclass(frozen=True, kw_only=True)
class LekkerladenBinaryDescription(BinarySensorEntityDescription):
    value_fn: Callable[[dict[str, Any]], bool | None]


def _computed(data: dict[str, Any]) -> dict[str, Any]:
    return data.get("computed") or {}


def _first_account(data: dict[str, Any]) -> dict[str, Any]:
    accounts = data.get("accounts") or []
    return accounts[0] if accounts else {}


ACCOUNT_BINARY: tuple[LekkerladenBinaryDescription, ...] = (
    LekkerladenBinaryDescription(
        key="contract_active",
        translation_key="contract_active",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        value_fn=lambda d: bool((_computed(d).get("mandate") or {}).get("active")),
    ),
    LekkerladenBinaryDescription(
        key="provider_token_valid",
        translation_key="provider_token_valid",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        value_fn=lambda d: _first_account(d).get("validToken"),
    ),
)


@dataclass(frozen=True, kw_only=True)
class ChargerBinaryDescription(BinarySensorEntityDescription):
    value_fn: Callable[[dict[str, Any]], bool | None]


CHARGER_BINARY: tuple[ChargerBinaryDescription, ...] = (
    ChargerBinaryDescription(
        key="mid_certified",
        translation_key="mid_certified",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:check-decagram",
        value_fn=lambda charger: charger.get("midCertified"),
    ),
    ChargerBinaryDescription(
        key="manual_session_upload",
        translation_key="manual_session_upload",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda charger: charger.get("manualSessionUploadTaskOpen"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LekkerladenConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    user_id = entry.data.get(CONF_USER_ID) or entry.unique_id or entry.entry_id
    entities: list[BinarySensorEntity] = [
        LekkerladenAccountBinary(coordinator, user_id, description)
        for description in ACCOUNT_BINARY
    ]
    for charger in coordinator.data.get("chargers") or []:
        charger_id = charger.get("id")
        if not charger_id:
            continue
        for description in CHARGER_BINARY:
            entities.append(
                LekkerladenChargerBinary(coordinator, user_id, charger_id, description)
            )
    async_add_entities(entities)


class LekkerladenAccountBinary(
    CoordinatorEntity[LekkerladenCoordinator], BinarySensorEntity
):
    _attr_has_entity_name = True
    _attr_attribution = ATTRIBUTION
    entity_description: LekkerladenBinaryDescription

    def __init__(
        self,
        coordinator: LekkerladenCoordinator,
        user_id: str,
        description: LekkerladenBinaryDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{user_id}_{description.key}"
        self._attr_device_info = account_device(str(user_id), coordinator.data or {})

    @property
    def is_on(self) -> bool | None:
        value = self.entity_description.value_fn(self.coordinator.data or {})
        if value is None:
            return None
        return bool(value)


class LekkerladenChargerBinary(
    CoordinatorEntity[LekkerladenCoordinator], BinarySensorEntity
):
    _attr_has_entity_name = True
    _attr_attribution = ATTRIBUTION
    entity_description: ChargerBinaryDescription

    def __init__(
        self,
        coordinator: LekkerladenCoordinator,
        user_id: str,
        charger_id: str,
        description: ChargerBinaryDescription,
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

    @property
    def is_on(self) -> bool | None:
        charger = self._charger()
        if not charger:
            return None
        value = self.entity_description.value_fn(charger)
        if value is None:
            return None
        return bool(value)
