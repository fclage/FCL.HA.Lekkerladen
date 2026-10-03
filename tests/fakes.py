"""HTTP and Home Assistant stand-ins shared by the unit tests."""

from __future__ import annotations

import json
from typing import Any

import ha_free  # noqa: F401

from lekkerladen_noha.const import (
    PATH_ACCOUNTS,
    PATH_CHARGERS,
    PATH_CONTRACT,
    PATH_ERE_RATE,
    PATH_GET_SESSION,
    PATH_PROFILE,
    PATH_SESSIONS,
    PATH_SESSIONS_MONTHLY,
)

OMIT = object()


class RawBody:
    def __init__(self, text: str) -> None:
        self.text = text


class FakeResponse:
    def __init__(self, status: int, payload: Any) -> None:
        self.status = status
        self._payload = payload

    async def text(self) -> str:
        if isinstance(self._payload, RawBody):
            return self._payload.text
        if self._payload is None:
            return "null"
        if isinstance(self._payload, str):
            return self._payload
        return json.dumps(self._payload)

    async def __aenter__(self) -> FakeResponse:
        return self

    async def __aexit__(self, *args: object) -> bool:
        return False


class FakeSession:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict[str, Any] | None, dict[str, str]]] = []
        self.routes: dict[tuple[str, str], tuple[int, Any]] = {}

    def add(self, method: str, url: str, status: int, payload: Any) -> None:
        self.routes[(method.upper(), url)] = (status, payload)

    def request(
        self,
        method: str,
        url: str,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: object = None,
    ) -> FakeResponse:
        self.calls.append((method.upper(), url, json, headers or {}))
        status, payload = self.routes[(method.upper(), url)]
        if isinstance(payload, BaseException):
            raise payload
        return FakeResponse(status, payload)


class FakeEntry:
    def __init__(self, data: dict[str, Any] | None = None) -> None:
        self.data = dict(data or {})
        self.runtime_data: Any = None
        self.unique_id = "uid-1"
        self.entry_id = "entry-1"


class FakeConfigEntries:
    def __init__(self) -> None:
        self.updates: list[dict[str, Any]] = []
        self.forwarded: tuple[Any, Any] | None = None
        self.unloaded: tuple[Any, Any] | None = None

    def async_update_entry(self, entry: FakeEntry, data: dict[str, Any]) -> None:
        entry.data = data
        self.updates.append(data)

    async def async_forward_entry_setups(self, entry: FakeEntry, platforms: list[object]) -> None:
        self.forwarded = (entry, platforms)

    async def async_unload_platforms(self, entry: FakeEntry, platforms: list[object]) -> bool:
        self.unloaded = (entry, platforms)
        return True


class FakeHass:
    def __init__(self, session: FakeSession | None = None) -> None:
        self.session = session
        self.config_entries = FakeConfigEntries()


def install_dashboard(
    session: FakeSession,
    *,
    token: str | None = "tok-live",
    expires: str | None = "2026-12-01T00:00:00Z",
    commission: Any = 0.2,
    include_token: bool = True,
) -> None:
    """Prime the calls made by LekkerladenApi.fetch_dashboard."""
    session.routes.clear()
    session.calls.clear()
    session_body: dict[str, Any] = {"id": "sess"}
    if expires is not None:
        session_body["expiresAt"] = expires
    if include_token:
        session_body["token"] = token
    session.add(
        "GET",
        PATH_GET_SESSION,
        200,
        {"session": session_body, "user": {"id": "user-1", "email": "a@b.co"}},
    )
    session.add(
        "GET",
        PATH_PROFILE,
        200,
        {"profile": {"firstName": "Ada", "lastName": "Lovelace", "payoutFrequency": "monthly"}},
    )
    session.add(
        "GET",
        PATH_CHARGERS,
        200,
        {"chargers": [{"id": "prov:1", "name": "Driveway"}, "skip-me"]},
    )
    session.add(
        "GET",
        PATH_ACCOUNTS,
        200,
        {"accounts": [{"validToken": True, "lastFetchedDate": "2026-08-02T00:00:00Z"}]},
    )
    session.add(
        "GET",
        PATH_SESSIONS_MONTHLY,
        200,
        {
            "data": {
                "months": [
                    {"yearMonth": "2026-08", "totalKwh": 10, "sessionCount": 2},
                    {"yearMonth": "2026-01", "totalKwh": "bad", "sessionCount": "bad"},
                ]
            }
        },
    )
    session.add(
        "GET",
        PATH_ERE_RATE,
        200,
        {"erePrice": 1.2, "perKwh": 0.15, "date": "2026-08-01"},
    )
    mandate: dict[str, Any] = {"active": True, "consentExpiresAt": "2027-01-01T00:00:00Z"}
    if commission is not OMIT:
        mandate["commissionRate"] = commission
    session.add("GET", PATH_CONTRACT, 200, {"mandate": mandate})
    session.add(
        "POST",
        PATH_SESSIONS,
        200,
        {
            "data": [
                {
                    "chargerId": "1",
                    "energyDeliveredKwh": 6.5,
                    "startTime": "2026-08-02T10:00:00Z",
                    "endTime": "2026-08-02T12:00:00Z",
                    "sessionId": "s1",
                    "isCertified": True,
                    "isComplete": True,
                    "providerId": "prov",
                }
            ]
        },
    )
