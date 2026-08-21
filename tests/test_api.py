"""Unit tests for the Lekkerladen HTTP client (mocked aiohttp)."""

from __future__ import annotations

import json
import unittest
from typing import Any

import ha_free  # noqa: E402, F401  # registers lekkerladen_noha package

from lekkerladen_noha.api import LekkerladenApi  # noqa: E402
from lekkerladen_noha.const import (  # noqa: E402
    PATH_CHARGERS,
    PATH_GET_SESSION,
    PATH_SEND_OTP,
    PATH_SESSIONS_MONTHLY,
    PATH_SIGN_IN,
)
from lekkerladen_noha.exceptions import (  # noqa: E402
    LekkerladenAuthError,
    LekkerladenCannotConnect,
)


class FakeResponse:
    def __init__(self, status: int, payload: Any) -> None:
        self.status = status
        self._payload = payload

    async def text(self) -> str:
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
        return FakeResponse(status, payload)


class ApiTest(unittest.IsolatedAsyncioTestCase):
    async def test_send_otp_payload(self) -> None:
        session = FakeSession()
        session.add("POST", PATH_SEND_OTP, 200, {"ok": True})
        api = LekkerladenApi(session)  # type: ignore[arg-type]
        await api.send_otp("user@example.com")
        method, url, body, headers = session.calls[0]
        self.assertEqual(method, "POST")
        self.assertEqual(url, PATH_SEND_OTP)
        self.assertEqual(body, {"email": "user@example.com", "type": "sign-in"})
        self.assertEqual(headers["X-Sign-Up-Flow"], "false")
        self.assertNotIn("Authorization", headers)

    async def test_sign_in_stores_token(self) -> None:
        session = FakeSession()
        session.add(
            "POST",
            PATH_SIGN_IN,
            200,
            {"token": "tok-1", "user": {"id": "abc", "email": "user@example.com"}},
        )
        api = LekkerladenApi(session)  # type: ignore[arg-type]
        result = await api.sign_in("user@example.com", "123456")
        self.assertEqual(result["token"], "tok-1")
        self.assertEqual(api.token, "tok-1")

    async def test_sign_in_invalid_otp(self) -> None:
        session = FakeSession()
        session.add(
            "POST",
            PATH_SIGN_IN,
            400,
            {"code": "INVALID_OTP", "message": "Invalid OTP"},
        )
        api = LekkerladenApi(session)  # type: ignore[arg-type]
        with self.assertRaises(LekkerladenAuthError):
            await api.sign_in("user@example.com", "000000")

    async def test_get_chargers_sends_bearer(self) -> None:
        session = FakeSession()
        session.add(
            "GET",
            PATH_CHARGERS,
            200,
            {"ok": True, "chargers": [{"id": "tesla:1", "name": "Wall Connector"}]},
        )
        api = LekkerladenApi(session, token="tok-1")  # type: ignore[arg-type]
        chargers = await api.get_chargers()
        self.assertEqual(chargers[0]["name"], "Wall Connector")
        self.assertEqual(session.calls[0][3]["Authorization"], "Bearer tok-1")

    async def test_401_is_auth_error(self) -> None:
        session = FakeSession()
        session.add("GET", PATH_GET_SESSION, 401, "Unauthorized")
        api = LekkerladenApi(session, token="expired")  # type: ignore[arg-type]
        with self.assertRaises(LekkerladenAuthError):
            await api.get_session()

    async def test_monthly_unwrap(self) -> None:
        session = FakeSession()
        session.add(
            "GET",
            PATH_SESSIONS_MONTHLY,
            200,
            {"ok": True, "data": {"months": [{"yearMonth": "2026-08", "totalKwh": 40}]}},
        )
        api = LekkerladenApi(session, token="tok-1")  # type: ignore[arg-type]
        months = await api.get_sessions_monthly()
        self.assertEqual(months[0]["yearMonth"], "2026-08")

    async def test_http_500(self) -> None:
        session = FakeSession()
        session.add("GET", PATH_CHARGERS, 500, "Internal server error")
        api = LekkerladenApi(session, token="tok-1")  # type: ignore[arg-type]
        with self.assertRaises(LekkerladenCannotConnect):
            await api.get_chargers()


if __name__ == "__main__":
    unittest.main()
