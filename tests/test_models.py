"""Unit tests for Lekkerladen payload helpers (no Home Assistant)."""

from __future__ import annotations

import unittest
from datetime import datetime, timezone

import ha_free  # noqa: E402, F401  # registers lekkerladen_noha package

from lekkerladen_noha.models import (  # noqa: E402
    current_year_month,
    estimate_eur,
    match_charger_sessions,
    month_energy_kwh,
    month_session_count,
    net_eur_per_kwh,
    parse_iso,
    year_energy_kwh,
    year_session_count,
)

MONTHS = [
    {"month": "Jan", "yearMonth": "2026-01", "totalKwh": None, "sessionCount": 0},
    {"month": "Jun", "yearMonth": "2026-06", "totalKwh": 100.5, "sessionCount": 8},
    {"month": "Jul", "yearMonth": "2026-07", "totalKwh": 200.25, "sessionCount": 22},
    {"month": "Aug", "yearMonth": "2026-08", "totalKwh": 40.0, "sessionCount": 3},
]

CHARGER = {
    "id": "tesla:site:charger-remote",
    "remoteId": "site:charger-remote",
    "serialNumber": "PGT000",
}


class ModelsTest(unittest.TestCase):
    def test_month_and_year_totals(self) -> None:
        self.assertAlmostEqual(month_energy_kwh(MONTHS, "2026-08") or 0, 40.0)
        self.assertEqual(month_session_count(MONTHS, "2026-08"), 3)
        self.assertIsNone(month_energy_kwh(MONTHS, "2026-01"))
        self.assertAlmostEqual(year_energy_kwh(MONTHS, 2026), 340.75)
        self.assertEqual(year_session_count(MONTHS, 2026), 33)
        self.assertEqual(year_energy_kwh(MONTHS, 2025), 0)

    def test_net_rate_and_estimate(self) -> None:
        rate = net_eur_per_kwh({"perKwh": 0.157}, 0.2)
        self.assertIsNotNone(rate)
        assert rate is not None
        self.assertAlmostEqual(rate, 0.157 * 0.8)
        payout = estimate_eur(100.0, rate)
        assert payout is not None
        self.assertAlmostEqual(payout, 12.56)

    def test_match_sessions_by_remote_id(self) -> None:
        sessions = [
            {"chargerId": "site:charger-remote", "energyDeliveredKwh": 6.8},
            {"chargerId": "other", "energyDeliveredKwh": 1.0},
        ]
        matched = match_charger_sessions(CHARGER, sessions)
        self.assertEqual(len(matched), 1)
        self.assertEqual(matched[0]["energyDeliveredKwh"], 6.8)

    def test_current_year_month(self) -> None:
        now = datetime(2026, 8, 21, 12, tzinfo=timezone.utc)
        self.assertEqual(current_year_month(now), "2026-08")

    def test_parse_iso(self) -> None:
        dt = parse_iso("2026-08-17T22:59:00.000Z")
        self.assertIsNotNone(dt)
        assert dt is not None
        self.assertEqual(dt.year, 2026)
        self.assertEqual(dt.month, 8)
        self.assertIsNone(parse_iso(None))
        self.assertIsNone(parse_iso("not-a-date"))


if __name__ == "__main__":
    unittest.main()
