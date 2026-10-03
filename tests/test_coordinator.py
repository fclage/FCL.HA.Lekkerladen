"""Coordinator refresh: token rotation, expiry, and error mapping."""

from __future__ import annotations

import unittest
from unittest.mock import patch

import ha_free  # noqa: F401

from fakes import OMIT, FakeEntry, FakeHass, FakeSession, install_dashboard
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed
from lekkerladen_noha.api import LekkerladenApi
from lekkerladen_noha.const import CONF_EXPIRES_AT, CONF_TOKEN, PATH_CONTRACT, PATH_GET_SESSION
from lekkerladen_noha.coordinator import LekkerladenCoordinator


class CoordinatorTest(unittest.IsolatedAsyncioTestCase):
    def _coordinator(
        self,
        session: FakeSession,
        data: dict[str, object] | None = None,
        token: str | None = "tok-old",
    ) -> LekkerladenCoordinator:
        entry = FakeEntry(
            {
                CONF_TOKEN: token,
                CONF_EXPIRES_AT: "2026-01-01T00:00:00Z",
            }
        )
        if data is not None:
            entry.data.update(data)
        api = LekkerladenApi(session, token=token)  # type: ignore[arg-type]
        hass = FakeHass(session)
        return LekkerladenCoordinator(hass, api, entry)  # type: ignore[arg-type]

    async def test_rotated_token_is_stored(self) -> None:
        session = FakeSession()
        install_dashboard(session, token="tok-new", expires="2026-12-01T00:00:00Z")
        coordinator = self._coordinator(session)
        with (
            patch("lekkerladen_noha.coordinator.current_year", return_value=2026),
            patch("lekkerladen_noha.coordinator.current_year_month", return_value="2026-08"),
        ):
            data = await coordinator._async_update_data()
        self.assertEqual(coordinator.api.token, "tok-new")
        self.assertEqual(coordinator.entry.data[CONF_TOKEN], "tok-new")
        self.assertEqual(coordinator.entry.data[CONF_EXPIRES_AT], "2026-12-01T00:00:00Z")
        computed = data["computed"]
        self.assertEqual(computed["year"], 2026)
        self.assertEqual(computed["year_month"], "2026-08")
        self.assertEqual(computed["month_kwh"], 10)
        self.assertEqual(computed["month_sessions"], 2)
        self.assertEqual(computed["ytd_kwh"], 10)
        self.assertEqual(computed["ytd_sessions"], 2)
        self.assertAlmostEqual(computed["net_eur_per_kwh"], 0.12)
        self.assertAlmostEqual(computed["month_eur"], 1.2)
        self.assertEqual(computed["mandate"]["active"], True)
        self.assertIsNotNone(computed["session_expires"])
        self.assertEqual(len(coordinator.hass.config_entries.updates), 1)

    async def test_expiry_only_and_unchanged_session(self) -> None:
        session = FakeSession()
        install_dashboard(session, token="tok-old", expires="2026-06-01T00:00:00Z", include_token=False)
        coordinator = self._coordinator(session, token="tok-old")
        with (
            patch("lekkerladen_noha.coordinator.current_year", return_value=2026),
            patch("lekkerladen_noha.coordinator.current_year_month", return_value="2026-08"),
        ):
            data = await coordinator._async_update_data()
        self.assertEqual(coordinator.api.token, "tok-old")
        self.assertEqual(coordinator.entry.data[CONF_EXPIRES_AT], "2026-06-01T00:00:00Z")
        self.assertEqual(coordinator.entry.data[CONF_TOKEN], "tok-old")

        install_dashboard(session, token="tok-old", expires="2026-06-01T00:00:00Z")
        with (
            patch("lekkerladen_noha.coordinator.current_year", return_value=2026),
            patch("lekkerladen_noha.coordinator.current_year_month", return_value="2026-08"),
        ):
            await coordinator._async_update_data()
        self.assertEqual(len(coordinator.hass.config_entries.updates), 1)
        self.assertIn("computed", data)

    async def test_missing_token_and_bad_commission(self) -> None:
        session = FakeSession()
        install_dashboard(
            session,
            include_token=False,
            expires="2026-07-01T00:00:00Z",
            commission="nope",
        )
        coordinator = self._coordinator(session, token=None)
        with (
            patch("lekkerladen_noha.coordinator.current_year", return_value=2026),
            patch("lekkerladen_noha.coordinator.current_year_month", return_value="2026-08"),
        ):
            data = await coordinator._async_update_data()
        self.assertIsNone(data["computed"]["commission_rate"])
        self.assertAlmostEqual(data["computed"]["net_eur_per_kwh"], 0.15)
        self.assertEqual(coordinator.entry.data[CONF_EXPIRES_AT], "2026-07-01T00:00:00Z")

        session.add(
            "GET",
            PATH_CONTRACT,
            200,
            {"mandate": {"active": True, "commissionRate": {"bad": True}}},
        )
        with (
            patch("lekkerladen_noha.coordinator.current_year", return_value=2026),
            patch("lekkerladen_noha.coordinator.current_year_month", return_value="2026-08"),
        ):
            data = await coordinator._async_update_data()
        self.assertIsNone(data["computed"]["commission_rate"])

        install_dashboard(session, token=None, include_token=False, expires=None, commission=OMIT)
        coordinator.entry.data[CONF_EXPIRES_AT] = None
        with (
            patch("lekkerladen_noha.coordinator.current_year", return_value=2026),
            patch("lekkerladen_noha.coordinator.current_year_month", return_value="2026-08"),
        ):
            data = await coordinator._async_update_data()
        self.assertIsNone(data["computed"]["commission_rate"])
        self.assertIsNone(data["computed"]["session_expires"])

    async def test_auth_and_network_errors(self) -> None:
        session = FakeSession()
        session.add("GET", PATH_GET_SESSION, 200, None)
        coordinator = self._coordinator(session)
        with self.assertRaises(ConfigEntryAuthFailed):
            await coordinator._async_update_data()

        session.add("GET", PATH_GET_SESSION, 500, "down")
        with self.assertRaises(UpdateFailed):
            await coordinator._async_update_data()
