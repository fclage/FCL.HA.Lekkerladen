"""Entities, diagnostics, and setup without a Home Assistant runtime."""

from __future__ import annotations

import unittest

import ha_free  # noqa: F401

from fakes import FakeEntry, FakeHass, FakeSession, install_dashboard
from homeassistant.const import CONF_EMAIL
from lekkerladen_noha import PLATFORMS, async_setup_entry, async_unload_entry, binary_sensor, sensor
from lekkerladen_noha.api import LekkerladenApi
from lekkerladen_noha.const import CONF_TOKEN, CONF_USER_ID
from lekkerladen_noha.coordinator import LekkerladenCoordinator
from lekkerladen_noha.diagnostics import async_get_config_entry_diagnostics
from lekkerladen_noha.entity import account_device, charger_device
from lekkerladen_noha.models import parse_iso


def _coordinator(data: dict[str, object]) -> LekkerladenCoordinator:
    session = FakeSession()
    entry = FakeEntry({CONF_TOKEN: "tok", CONF_USER_ID: "user-1"})
    api = LekkerladenApi(session, token="tok")  # type: ignore[arg-type]
    coordinator = LekkerladenCoordinator(FakeHass(session), api, entry)  # type: ignore[arg-type]
    coordinator.data = data
    entry.runtime_data = coordinator
    return coordinator


def _dashboard() -> dict[str, object]:
    return {
        "computed": {
            "year": 2026,
            "year_month": "2026-08",
            "month_kwh": 10.5,
            "month_sessions": 2,
            "ytd_kwh": 40,
            "ytd_sessions": 8,
            "ere_price": 1.1,
            "ere_per_kwh": 0.15,
            "ere_date": "2026-08-01",
            "commission_rate": 0.2,
            "net_eur_per_kwh": 0.12,
            "month_eur": 1.26,
            "ytd_eur": 4.8,
            "mandate": {"active": True, "consentExpiresAt": "2027-01-01T00:00:00Z"},
            "session_expires": parse_iso("2026-12-01T00:00:00Z"),
        },
        "profile": {
            "firstName": "Ada",
            "lastName": "Lovelace",
            "payoutFrequency": "monthly",
            "partner": "acme",
            "email": "ada@example.com",
        },
        "accounts": [
            {
                "validToken": True,
                "lastFetchedDate": "2026-08-02T00:00:00Z",
                "email": "ada@example.com",
            }
        ],
        "chargers": [
            {},
            {
                "id": "prov:1",
                "remoteId": "1",
                "name": "Driveway",
                "providerId": "tesla",
                "productName": "Wall",
                "serialNumber": "SN1",
                "midCertified": True,
                "manualSessionUploadTaskOpen": False,
            },
        ],
        "sessions": [
            {
                "chargerId": "1",
                "energyDeliveredKwh": 6.5,
                "startTime": "2026-08-02T10:00:00Z",
                "endTime": "2026-08-02T12:00:00Z",
                "sessionId": "s1",
                "isCertified": True,
                "isComplete": False,
                "providerId": "tesla",
            }
        ],
    }


class EntityTest(unittest.TestCase):
    def test_device_info(self) -> None:
        named = account_device("user-1", {"profile": {"firstName": "Ada", "lastName": "Lovelace"}})
        self.assertEqual(named.name, "Ada Lovelace")
        self.assertEqual(named.identifiers, {("lekkerladen", "user-1")})
        self.assertEqual(account_device("user-1", {}).name, "Lekkerladen")
        self.assertEqual(account_device("user-1", None).name, "Lekkerladen")
        self.assertEqual(account_device("user-1", {"profile": {"firstName": "Ada"}}).name, "Ada")

        charger = charger_device(
            "user-1",
            {"id": "prov:1", "providerId": "tesla", "name": "Driveway", "productName": "Wall", "serialNumber": "SN1"},
        )
        self.assertEqual(charger.manufacturer, "Tesla")
        self.assertEqual(charger.model, "Wall")
        self.assertEqual(charger.via_device, ("lekkerladen", "user-1"))
        plain = charger_device("user-1", {"id": "x", "productCode": "P1"})
        self.assertEqual(plain.manufacturer, "Lekkerladen")
        self.assertEqual(plain.name, "EV charger")
        self.assertEqual(plain.model, "P1")


class PlatformTest(unittest.IsolatedAsyncioTestCase):
    async def test_sensors_and_binary_sensors(self) -> None:
        coordinator = _coordinator(_dashboard())
        entry = coordinator.entry
        added: list[object] = []
        await sensor.async_setup_entry(FakeHass(), entry, added.extend)  # type: ignore[arg-type]
        self.assertEqual(len(added), 18)

        values = {entity.entity_description.key: entity.native_value for entity in added}
        self.assertEqual(values["month_energy"], 10.5)
        self.assertEqual(values["payout_frequency"], "monthly")
        self.assertEqual(values["partner"], "acme")
        self.assertEqual(values["latest_session_energy"], 6.5)
        self.assertEqual(values["serial_number"], "SN1")
        self.assertIsNotNone(values["latest_session_start"])
        self.assertIsNotNone(values["account_last_fetched"])
        self.assertIsNotNone(values["contract_expires"])

        by_key = {entity.entity_description.key: entity for entity in added}
        self.assertEqual(by_key["ere_price"].extra_state_attributes["rate_date"], "2026-08-01")
        self.assertEqual(by_key["net_per_kwh"].extra_state_attributes["commission_rate"], 0.2)
        self.assertIsNone(by_key["month_energy"].extra_state_attributes)
        latest = by_key["latest_session_energy"].extra_state_attributes
        self.assertEqual(latest["session_id"], "s1")
        self.assertIsNone(by_key["serial_number"].extra_state_attributes)
        self.assertEqual(by_key["ytd_energy"].last_reset.year, 2026)
        self.assertEqual(by_key["ytd_energy"].last_reset.month, 1)
        self.assertEqual(by_key["month_energy"].last_reset.month, 8)
        self.assertEqual(by_key["month_sessions"].last_reset.day, 1)
        self.assertEqual(by_key["ytd_sessions"].last_reset.year, 2026)
        self.assertIsNone(by_key["ere_price"].last_reset)

        coordinator.data["computed"]["year"] = None
        coordinator.data["computed"]["year_month"] = "2026-8"
        self.assertIsNone(by_key["ytd_energy"].last_reset)
        self.assertIsNone(by_key["month_energy"].last_reset)
        self.assertIsNone(by_key["ytd_sessions"].last_reset)

        coordinator.data["accounts"] = []
        self.assertIsNone(by_key["account_last_fetched"].native_value)
        coordinator.data["sessions"] = []
        self.assertIsNone(by_key["latest_session_energy"].native_value)
        self.assertIsNone(by_key["latest_session_energy"].extra_state_attributes)
        coordinator.data["chargers"] = []
        self.assertIsNone(by_key["serial_number"].native_value)

        binary: list[object] = []
        coordinator.data = _dashboard()
        await binary_sensor.async_setup_entry(FakeHass(), entry, binary.extend)  # type: ignore[arg-type]
        self.assertEqual(len(binary), 4)
        states = {entity.entity_description.key: entity.is_on for entity in binary}
        self.assertEqual(states["contract_active"], True)
        self.assertEqual(states["provider_token_valid"], True)
        self.assertEqual(states["mid_certified"], True)
        self.assertEqual(states["manual_session_upload"], False)

        coordinator.data["accounts"][0]["validToken"] = None
        coordinator.data["chargers"][1]["midCertified"] = None
        token = next(entity for entity in binary if entity.entity_description.key == "provider_token_valid")
        mid = next(entity for entity in binary if entity.entity_description.key == "mid_certified")
        self.assertIsNone(token.is_on)
        self.assertIsNone(mid.is_on)
        coordinator.data["chargers"] = []
        self.assertIsNone(mid.is_on)
        coordinator.data["computed"] = {}
        contract = next(entity for entity in binary if entity.entity_description.key == "contract_active")
        self.assertEqual(contract.is_on, False)

    async def test_user_id_fallback(self) -> None:
        coordinator = _coordinator(_dashboard())
        entry = coordinator.entry
        entry.data = {CONF_TOKEN: "tok"}
        entry.unique_id = "from-unique"
        added: list[object] = []
        await sensor.async_setup_entry(FakeHass(), entry, added.extend)  # type: ignore[arg-type]
        self.assertTrue(added[0]._attr_unique_id.startswith("from-unique_"))

        entry.unique_id = ""
        entry.entry_id = "from-entry"
        added.clear()
        await binary_sensor.async_setup_entry(FakeHass(), entry, added.extend)  # type: ignore[arg-type]
        self.assertTrue(added[0]._attr_unique_id.startswith("from-entry_"))


class DiagnosticsTest(unittest.IsolatedAsyncioTestCase):
    async def test_redacts_secrets(self) -> None:
        coordinator = _coordinator(_dashboard())
        coordinator.entry.data = {
            CONF_TOKEN: "secret",
            CONF_EMAIL: "ada@example.com",
            CONF_USER_ID: "user-1",
        }
        result = await async_get_config_entry_diagnostics(FakeHass(), coordinator.entry)  # type: ignore[arg-type]
        self.assertEqual(result["entry"][CONF_TOKEN], "**REDACTED**")
        self.assertEqual(result["entry"][CONF_USER_ID], "user-1")
        self.assertEqual(result["data"]["profile"]["email"], "**REDACTED**")
        self.assertEqual(result["data"]["profile"]["firstName"], "Ada")

        coordinator.data = None
        empty = await async_get_config_entry_diagnostics(FakeHass(), coordinator.entry)  # type: ignore[arg-type]
        self.assertEqual(empty["data"], {})


class SetupTest(unittest.IsolatedAsyncioTestCase):
    async def test_setup_and_unload(self) -> None:
        session = FakeSession()
        install_dashboard(session, token="tok-live")
        entry = FakeEntry({CONF_TOKEN: "tok-old", CONF_USER_ID: "user-1"})
        hass = FakeHass(session)
        self.assertTrue(await async_setup_entry(hass, entry))  # type: ignore[arg-type]
        self.assertIsInstance(entry.runtime_data, LekkerladenCoordinator)
        self.assertEqual(entry.runtime_data.api.token, "tok-live")
        self.assertEqual(hass.config_entries.forwarded[1], PLATFORMS)
        self.assertTrue(await async_unload_entry(hass, entry))  # type: ignore[arg-type]
        self.assertEqual(hass.config_entries.unloaded[1], PLATFORMS)
