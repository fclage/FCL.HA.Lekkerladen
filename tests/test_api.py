"""Unit tests for the Lekkerladen HTTP client (mocked aiohttp)."""

from __future__ import annotations

import unittest

import ha_free  # noqa: E402, F401  # registers lekkerladen_noha package
from aiohttp import ClientError  # noqa: E402

from fakes import FakeSession, RawBody  # noqa: E402
from lekkerladen_noha.api import (  # noqa: E402
    LekkerladenApi,
    _error_message,
    _list_field,
    _looks_like_auth,
    _maybe_json,
)
from lekkerladen_noha.const import (  # noqa: E402
    PATH_ACCOUNTS,
    PATH_CHARGERS,
    PATH_CONTRACT,
    PATH_ERE_RATE,
    PATH_GET_SESSION,
    PATH_PROFILE,
    PATH_SEND_OTP,
    PATH_SESSIONS,
    PATH_SESSIONS_MONTHLY,
    PATH_SIGN_IN,
)
from lekkerladen_noha.exceptions import (  # noqa: E402
    LekkerladenAuthError,
    LekkerladenCannotConnect,
)


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


class ApiBranchTest(unittest.IsolatedAsyncioTestCase):
    def _api(self, session: FakeSession | None = None, token: str | None = "tok-1") -> tuple[LekkerladenApi, FakeSession]:
        http = session or FakeSession()
        return LekkerladenApi(http, token=token), http  # type: ignore[arg-type]

    async def test_set_token(self) -> None:
        api, _session = self._api(token=None)
        self.assertIsNone(api.token)
        api.set_token("next")
        self.assertEqual(api.token, "next")

    async def test_send_otp_error_shapes(self) -> None:
        api, session = self._api(token=None)
        for payload in (
            {"error": {"message": "mailbox full"}},
            {"error": {"code": "LOCKED"}},
            {"error": {"message": ""}},
            {"error": "nope"},
        ):
            session.add("POST", PATH_SEND_OTP, 200, payload)
            with self.assertRaises(LekkerladenAuthError):
                await api.send_otp("user@example.com")

    async def test_sign_in_rejects_bad_payloads(self) -> None:
        api, session = self._api(token=None)
        for payload in (["nope"], {"error": "bad"}, {}, {"token": ""}):
            session.add("POST", PATH_SIGN_IN, 200, payload)
            with self.assertRaises(LekkerladenAuthError):
                await api.sign_in("user@example.com", "123456")
        self.assertIsNone(api.token)

    async def test_session_profile_and_lists(self) -> None:
        api, session = self._api()
        session.add("GET", PATH_GET_SESSION, 200, None)
        self.assertIsNone(await api.get_session())
        session.add("GET", PATH_GET_SESSION, 200, ["nope"])
        with self.assertRaises(LekkerladenCannotConnect):
            await api.get_session()

        session.add("GET", PATH_PROFILE, 200, {"profile": {"id": "p"}})
        self.assertEqual((await api.get_profile())["id"], "p")
        session.add("GET", PATH_PROFILE, 200, {"id": "raw"})
        self.assertEqual((await api.get_profile())["id"], "raw")
        session.add("GET", PATH_PROFILE, 200, {"profile": "x", "id": "raw"})
        self.assertEqual((await api.get_profile())["id"], "raw")
        session.add("GET", PATH_PROFILE, 200, ["nope"])
        self.assertIsNone(await api.get_profile())

        session.add("GET", PATH_ACCOUNTS, 200, {"accounts": [{"id": "a"}, "skip", 1]})
        self.assertEqual(await api.get_accounts(), [{"id": "a"}])
        session.add("GET", PATH_ACCOUNTS, 200, ["nope"])
        self.assertEqual(await api.get_accounts(), [])

        session.add("GET", PATH_ERE_RATE, 200, {"perKwh": 0.1})
        self.assertEqual((await api.get_ere_rate())["perKwh"], 0.1)
        session.add("GET", PATH_ERE_RATE, 200, "nope")
        self.assertEqual(await api.get_ere_rate(), {})
        session.add("GET", PATH_CONTRACT, 200, "nope")
        self.assertEqual(await api.get_contract(), {})
        session.add("GET", PATH_CONTRACT, 200, {"mandate": {"active": True}})
        self.assertEqual((await api.get_contract())["mandate"]["active"], True)

    async def test_monthly_and_sessions_empty(self) -> None:
        api, session = self._api()
        session.add("GET", PATH_SESSIONS_MONTHLY, 200, {"months": [{"yearMonth": "2026-08"}]})
        self.assertEqual((await api.get_sessions_monthly())[0]["yearMonth"], "2026-08")
        session.add("GET", PATH_SESSIONS_MONTHLY, 200, {"data": {"months": "nope"}})
        self.assertEqual(await api.get_sessions_monthly(), [])
        session.add("GET", PATH_SESSIONS_MONTHLY, 200, ["nope"])
        self.assertEqual(await api.get_sessions_monthly(), [])

        session.add("POST", PATH_SESSIONS, 200, {"data": [{"sessionId": "s1"}]})
        self.assertEqual((await api.get_sessions())[0]["sessionId"], "s1")
        session.add("POST", PATH_SESSIONS, 200, {"data": {"sessionId": "s1"}})
        self.assertEqual(await api.get_sessions(), [])
        session.add("POST", PATH_SESSIONS, 200, ["nope"])
        self.assertEqual(await api.get_sessions(), [])

    async def test_fetch_dashboard_and_missing_session(self) -> None:
        api, session = self._api()
        from fakes import install_dashboard

        install_dashboard(session, token="tok-live")
        dashboard = await api.fetch_dashboard()
        self.assertEqual(dashboard["chargers"][0]["id"], "prov:1")
        self.assertEqual(dashboard["accounts"][0]["validToken"], True)
        self.assertEqual(dashboard["monthly"][0]["yearMonth"], "2026-08")
        self.assertEqual(dashboard["sessions"][0]["sessionId"], "s1")

        session.add("GET", PATH_GET_SESSION, 200, None)
        with self.assertRaises(LekkerladenAuthError):
            await api.fetch_dashboard()
        session.add("GET", PATH_GET_SESSION, 200, {"user": {"id": "u"}})
        with self.assertRaises(LekkerladenAuthError):
            await api.fetch_dashboard()

    async def test_timeout_and_client_error(self) -> None:
        api, session = self._api()
        session.add("GET", PATH_GET_SESSION, 200, TimeoutError("slow"))
        with self.assertRaises(LekkerladenCannotConnect) as timeout:
            await api.get_session()
        self.assertIn("Timeout", str(timeout.exception))

        session.add("GET", PATH_GET_SESSION, 200, ClientError(""))
        with self.assertRaises(LekkerladenCannotConnect) as offline:
            await api.get_session()
        self.assertIn("Cannot connect", str(offline.exception))

    async def test_http_status_mapping(self) -> None:
        api, session = self._api()
        session.add("GET", PATH_CHARGERS, 400, {"message": "maintenance"})
        with self.assertRaises(LekkerladenCannotConnect):
            await api.get_chargers()
        session.add("GET", PATH_CHARGERS, 403, {"message": "nope", "code": "OTP_EXPIRED"})
        with self.assertRaises(LekkerladenAuthError):
            await api.get_chargers()
        session.add("GET", PATH_CHARGERS, 400, RawBody(""))
        with self.assertRaises(LekkerladenCannotConnect) as empty:
            await api.get_chargers()
        self.assertIn("HTTP 400", str(empty.exception))
        session.add("GET", PATH_ERE_RATE, 200, RawBody("{"))
        self.assertEqual(await api.get_ere_rate(), {})
        session.add("GET", PATH_ERE_RATE, 200, RawBody("undefined"))
        self.assertEqual(await api.get_ere_rate(), {})
        session.add("GET", PATH_ERE_RATE, 200, RawBody(""))
        self.assertEqual(await api.get_ere_rate(), {})

    def test_helper_edges(self) -> None:
        self.assertIsNone(_maybe_json(""))
        self.assertIsNone(_maybe_json("null"))
        self.assertIsNone(_maybe_json("undefined"))
        self.assertEqual(_maybe_json("{"), "{")
        self.assertEqual(_maybe_json("hello"), "hello")
        self.assertEqual(_maybe_json('{"a": 1}'), {"a": 1})

        self.assertEqual(_error_message({"error": {"message": "m"}}), "m")
        self.assertEqual(_error_message({"error": {"code": "c"}}), "c")
        self.assertEqual(_error_message({"error": {}, "message": "outer"}), "outer")
        self.assertEqual(_error_message({"code": "ONLY"}), "ONLY")
        self.assertEqual(_error_message({"error": "text"}), "text")
        self.assertEqual(_error_message("  plain  "), "plain")
        self.assertIsNone(_error_message({"error": {}}))
        self.assertIsNone(_error_message("  "))
        self.assertIsNone(_error_message(None))
        self.assertIsNone(_error_message([]))

        self.assertTrue(_looks_like_auth("bad otp", {}))
        self.assertTrue(_looks_like_auth("nope", {"code": "VALIDATION_ERROR"}))
        self.assertFalse(_looks_like_auth("maintenance", {"code": "OTHER"}))
        self.assertFalse(_looks_like_auth("maintenance", "x"))

        self.assertEqual(_list_field({"chargers": [{"id": "a"}, "nope"]}, "chargers"), [{"id": "a"}])
        self.assertEqual(_list_field({"chargers": "nope"}, "chargers"), [])
        self.assertEqual(_list_field(["nope"], "chargers"), [])


if __name__ == "__main__":
    unittest.main()
