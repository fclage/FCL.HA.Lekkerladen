"""Shared device metadata for Lekkerladen entities."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN


def account_device(user_id: str, data: dict[str, Any] | None) -> DeviceInfo:
    profile = (data or {}).get("profile") or {}
    name = " ".join(
        part for part in (profile.get("firstName"), profile.get("lastName")) if part
    )
    return DeviceInfo(
        identifiers={(DOMAIN, str(user_id))},
        manufacturer="Lekkerladen",
        name=name or "Lekkerladen",
        model="ERE account",
        configuration_url="https://app.lekkerladen.com/dashboard",
    )


def charger_device(user_id: str, charger: dict[str, Any]) -> DeviceInfo:
    charger_id = str(charger.get("id"))
    return DeviceInfo(
        identifiers={(DOMAIN, charger_id)},
        manufacturer=(charger.get("providerId") or "Lekkerladen").title(),
        name=charger.get("name") or "EV charger",
        model=charger.get("productName") or charger.get("productCode"),
        serial_number=charger.get("serialNumber"),
        via_device=(DOMAIN, str(user_id)),
        configuration_url="https://app.lekkerladen.com/mijn-laadpaal",
    )
