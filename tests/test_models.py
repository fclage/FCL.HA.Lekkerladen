"""Unit tests for Lekkerladen payload helpers (no Home Assistant)."""

from __future__ import annotations

import unittest
from datetime import datetime, timezone

import ha_free  # noqa: E402, F401  # registers lekkerladen_noha package

from lekkerladen_noha.models import (  # noqa: E402
    amsterdam_now,
    contract_mandate,
    current_year,
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
        self.assertIsNone(parse_iso(12))
        self.assertIsNone(parse_iso(""))

    def test_clock_helpers(self) -> None:
        now = amsterdam_now()
        self.assertIsNotNone(now.tzinfo)
        self.assertEqual(current_year(now), now.year)
        self.assertEqual(current_year(), now.year)
        self.assertEqual(current_year_month(), now.strftime("%Y-%m"))

    def test_missing_and_bad_numbers(self) -> None:
        self.assertIsNone(month_energy_kwh(MONTHS, "1999-01"))
        self.assertIsNone(month_session_count(MONTHS, "1999-01"))
        self.assertIsNone(
            month_energy_kwh([{"yearMonth": "2026-08", "totalKwh": ""}], "2026-08")
        )
        self.assertIsNone(
            month_energy_kwh([{"yearMonth": "2026-08", "totalKwh": "nope"}], "2026-08")
        )
        self.assertIsNone(
            month_session_count([{"yearMonth": "2026-08", "sessionCount": None}], "2026-08")
        )
        self.assertIsNone(
            month_session_count([{"yearMonth": "2026-08", "sessionCount": "x"}], "2026-08")
        )
        rows = [
            {"yearMonth": None, "totalKwh": 5, "sessionCount": 4},
            {"yearMonth": "2026-01", "totalKwh": "nope", "sessionCount": "nope"},
            {"yearMonth": "2026-02", "totalKwh": "", "sessionCount": None},
            {"yearMonth": "2026-03", "totalKwh": {}, "sessionCount": {}},
            {"yearMonth": "2026-04", "totalKwh": 2, "sessionCount": 1},
        ]
        self.assertEqual(year_energy_kwh(rows, 2026), 2)
        self.assertEqual(year_session_count(rows, 2026), 1)

    def test_rate_and_mandate_edges(self) -> None:
        self.assertIsNone(net_eur_per_kwh(None, 0.2))
        self.assertIsNone(net_eur_per_kwh({}, 0.2))
        self.assertIsNone(net_eur_per_kwh({"perKwh": "nope"}, 0.2))
        self.assertAlmostEqual(net_eur_per_kwh({"perKwh": "1.5"}, None) or 0, 1.5)
        self.assertIsNone(estimate_eur(None, 1.0))
        self.assertIsNone(estimate_eur(1.0, None))
        self.assertEqual(contract_mandate(None), {})
        self.assertEqual(contract_mandate({}), {})
        self.assertEqual(contract_mandate({"mandate": "nope"}), {})
        self.assertEqual(contract_mandate({"mandate": {"active": True}}), {"active": True})

    def test_match_id_shapes(self) -> None:
        charger = {"id": "prov:abc", "remoteId": ""}
        matched = match_charger_sessions(
            charger,
            [
                {"chargerId": ""},
                {"chargerId": "abc", "energyDeliveredKwh": 1},
                {"chargerId": "prov:abc", "energyDeliveredKwh": 2},
                {},
            ],
        )
        self.assertEqual([row["energyDeliveredKwh"] for row in matched], [1, 2])


if __name__ == "__main__":
    unittest.main()
