"""Pure helpers to shape Lekkerladen API payloads for sensors."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from .const import AMSTERDAM_TZ


def amsterdam_now() -> datetime:
    return datetime.now(ZoneInfo(AMSTERDAM_TZ))


def current_year_month(now: datetime | None = None) -> str:
    stamp = now or amsterdam_now()
    return stamp.strftime("%Y-%m")


def current_year(now: datetime | None = None) -> int:
    stamp = now or amsterdam_now()
    return stamp.year


def _as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def month_row(months: list[dict[str, Any]], year_month: str) -> dict[str, Any] | None:
    for row in months:
        if row.get("yearMonth") == year_month:
            return row
    return None


def month_energy_kwh(months: list[dict[str, Any]], year_month: str) -> float | None:
    row = month_row(months, year_month)
    if not row:
        return None
    return _as_float(row.get("totalKwh"))


def month_session_count(months: list[dict[str, Any]], year_month: str) -> int | None:
    row = month_row(months, year_month)
    if not row:
        return None
    count = row.get("sessionCount")
    if count is None:
        return None
    try:
        return int(count)
    except (TypeError, ValueError):
        return None


def year_energy_kwh(months: list[dict[str, Any]], year: int) -> float:
    prefix = f"{year}-"
    total = 0.0
    for row in months:
        ym = row.get("yearMonth") or ""
        if not str(ym).startswith(prefix):
            continue
        kwh = _as_float(row.get("totalKwh"))
        if kwh is not None:
            total += kwh
    return total


def year_session_count(months: list[dict[str, Any]], year: int) -> int:
    prefix = f"{year}-"
    total = 0
    for row in months:
        ym = row.get("yearMonth") or ""
        if not str(ym).startswith(prefix):
            continue
        try:
            total += int(row.get("sessionCount") or 0)
        except (TypeError, ValueError):
            continue
    return total


def net_eur_per_kwh(ere_rate: dict[str, Any] | None, commission_rate: float | None) -> float | None:
    if not ere_rate:
        return None
    per_kwh = _as_float(ere_rate.get("perKwh"))
    if per_kwh is None:
        return None
    fee = 0.0 if commission_rate is None else float(commission_rate)
    return per_kwh * (1.0 - fee)


def estimate_eur(kwh: float | None, net_rate: float | None) -> float | None:
    if kwh is None or net_rate is None:
        return None
    return kwh * net_rate


def contract_mandate(contract: dict[str, Any] | None) -> dict[str, Any]:
    if not contract:
        return {}
    mandate = contract.get("mandate")
    return mandate if isinstance(mandate, dict) else {}


def match_charger_sessions(
    charger: dict[str, Any], sessions: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Sessions use remoteId; charger.id is prefixed with provider."""
    charger_id = str(charger.get("id") or "")
    remote_id = str(charger.get("remoteId") or "")
    matched: list[dict[str, Any]] = []
    for session in sessions:
        sid = str(session.get("chargerId") or "")
        if not sid:
            continue
        if sid == remote_id or sid == charger_id or charger_id.endswith(f":{sid}"):
            matched.append(session)
    return matched


def parse_iso(value: Any) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
