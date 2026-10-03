"""Config flow steps without a Home Assistant runtime."""

from __future__ import annotations

import unittest

import ha_free  # noqa: F401

from fakes import FakeHass, FakeSession
from homeassistant.config_entries import SOURCE_REAUTH
from homeassistant.const import CONF_EMAIL
from lekkerladen_noha.config_flow import LekkerladenConfigFlow
from lekkerladen_noha.const import CONF_TOKEN, CONF_USER_ID, DOMAIN, PATH_SEND_OTP
from lekkerladen_noha.exceptions import LekkerladenAuthError, LekkerladenCannotConnect


class ScriptedApi:
    def __init__(
        self,
        otp: Exception | None = None,
        sign: Exception | None = None,
        session: object | None = None,
        signed: dict[str, object] | None = None,
    ) -> None:
        self.otp = otp
        self.sign = sign
        self.session = session
        self.signed = signed or {
            "token": "tok",
            "user": {"id": "user-1", "email": "a@b.co"},
        }
        self.sent: list[str] = []

    async def send_otp(self, email: str) -> None:
        self.sent.append(email)
        if self.otp:
            raise self.otp

    async def sign_in(self, email: str, otp: str) -> dict[str, object]:
        if self.sign:
            raise self.sign
        return self.signed

    async def get_session(self) -> object:
        if isinstance(self.session, Exception):
            raise self.session
        if self.session is None:
            return {
                "user": {"id": "user-1", "email": "a@b.co"},
                "session": {"token": "tok", "expiresAt": "2026-01-01T00:00:00Z"},
            }
        return self.session


class ConfigFlowTest(unittest.IsolatedAsyncioTestCase):
    def _flow(self, api: ScriptedApi | None = None) -> LekkerladenConfigFlow:
        flow = LekkerladenConfigFlow()
        flow.hass = FakeHass(FakeSession())  # type: ignore[assignment]
        flow.source = "user"  # type: ignore[attr-defined]
        if api is not None:
            flow._api = api  # type: ignore[assignment]
        return flow

    def test_domain(self) -> None:
        self.assertEqual(LekkerladenConfigFlow.domain, DOMAIN)

    async def test_user_step_validation_and_errors(self) -> None:
        flow = self._flow(ScriptedApi())
        form = await flow.async_step_user()
        self.assertEqual(form["step_id"], "user")
        self.assertEqual(form["errors"], {})

        for email in ("not-an-email", "a@localhost"):
            result = await flow.async_step_user({CONF_EMAIL: email})
            self.assertEqual(result["errors"]["base"], "invalid_email")

        flow = self._flow(ScriptedApi(otp=LekkerladenAuthError("no")))
        result = await flow.async_step_user({CONF_EMAIL: "A@B.CO"})
        self.assertEqual(flow._email, "a@b.co")
        self.assertEqual(result["errors"]["base"], "otp_send_failed")

        flow = self._flow(ScriptedApi(otp=LekkerladenCannotConnect("down")))
        result = await flow.async_step_user({CONF_EMAIL: "a@b.co"})
        self.assertEqual(result["errors"]["base"], "cannot_connect")

        flow = self._flow(ScriptedApi(otp=RuntimeError("boom")))
        with self.assertLogs("lekkerladen_noha.config_flow", level="ERROR"):
            result = await flow.async_step_user({CONF_EMAIL: "a@b.co"})
        self.assertEqual(result["errors"]["base"], "unknown")

    async def test_user_step_creates_client_and_opens_otp(self) -> None:
        flow = self._flow()
        session = FakeSession()
        session.add("POST", PATH_SEND_OTP, 200, {"ok": True})
        flow.hass.session = session  # type: ignore[attr-defined]
        result = await flow.async_step_user({CONF_EMAIL: "a@b.co"})
        self.assertEqual(result["step_id"], "otp")
        self.assertEqual(result["description_placeholders"]["email"], "a@b.co")
        self.assertEqual(session.calls[0][0], "POST")

    async def test_otp_step(self) -> None:
        flow = self._flow(ScriptedApi())
        flow._email = "a@b.co"
        form = await flow.async_step_otp()
        self.assertEqual(form["step_id"], "otp")

        short = await flow.async_step_otp({"otp": "12-ab"})
        self.assertEqual(short["errors"]["base"], "invalid_otp")

        created = await flow.async_step_otp({"otp": "123 456"})
        self.assertEqual(created["type"], "create_entry")
        self.assertEqual(created["title"], "a@b.co")
        self.assertEqual(created["data"][CONF_TOKEN], "tok")
        self.assertEqual(created["data"][CONF_USER_ID], "user-1")
        self.assertTrue(flow.checked_configured)  # type: ignore[attr-defined]

        flow = self._flow(ScriptedApi(sign=LekkerladenAuthError("bad")))
        result = await flow.async_step_otp({"otp": "123456"})
        self.assertEqual(result["errors"]["base"], "invalid_otp")

        flow = self._flow(ScriptedApi(sign=LekkerladenCannotConnect("down")))
        result = await flow.async_step_otp({"otp": "123456"})
        self.assertEqual(result["errors"]["base"], "cannot_connect")

        flow = self._flow(ScriptedApi(sign=RuntimeError("boom")))
        with self.assertLogs("lekkerladen_noha.config_flow", level="ERROR"):
            result = await flow.async_step_otp({"otp": "123456"})
        self.assertEqual(result["errors"]["base"], "unknown")

    async def test_finish_aborts_and_reauth(self) -> None:
        flow = self._flow(ScriptedApi())
        aborted = await flow._async_finish({"token": "tok"}, {"user": {}})
        self.assertEqual(aborted["reason"], "unknown")
        aborted = await flow._async_finish({"user": {"id": "user-1"}}, {"session": {}})
        self.assertEqual(aborted["reason"], "unknown")

        flow._email = None
        created = await flow._async_finish(
            {"token": "tok", "user": {"id": "user-1"}},
            {"session": {"expiresAt": "later"}},
        )
        self.assertEqual(created["title"], "Lekkerladen")
        self.assertIsNone(created["data"][CONF_EMAIL])

        flow.source = SOURCE_REAUTH  # type: ignore[attr-defined]
        flow.reauth_entry = {"entry": 1}  # type: ignore[attr-defined]
        updated = await flow._async_finish(
            {"token": "tok-2", "user": {"id": "user-1", "email": "a@b.co"}},
            {"session": {"token": "tok-2", "expiresAt": "later"}},
        )
        self.assertEqual(updated["reason"], "reauth_successful")
        self.assertEqual(flow.mismatch_reason, "wrong_account")  # type: ignore[attr-defined]
        self.assertEqual(flow.reauth_target, {"entry": 1})  # type: ignore[attr-defined]
        self.assertEqual(flow.reauth_updates[CONF_TOKEN], "tok-2")  # type: ignore[attr-defined]

    async def test_reauth_steps(self) -> None:
        flow = self._flow(ScriptedApi())
        opened = await flow.async_step_reauth({CONF_EMAIL: " User@Example.com "})
        self.assertEqual(flow._email, "user@example.com")
        self.assertEqual(opened["step_id"], "reauth_confirm")

        empty = await flow.async_step_reauth_confirm()
        self.assertEqual(empty["step_id"], "reauth_confirm")

        sent = await flow.async_step_reauth_confirm({CONF_EMAIL: ""})
        self.assertEqual(sent["step_id"], "otp")
        self.assertEqual(flow._api.sent, ["user@example.com"])  # type: ignore[attr-defined]

        flow = self._flow(ScriptedApi(otp=LekkerladenAuthError("no")))
        flow._email = "a@b.co"
        result = await flow.async_step_reauth_confirm({CONF_EMAIL: "a@b.co"})
        self.assertEqual(result["errors"]["base"], "otp_send_failed")

        flow = self._flow(ScriptedApi(otp=LekkerladenCannotConnect("down")))
        result = await flow.async_step_reauth_confirm({CONF_EMAIL: "a@b.co"})
        self.assertEqual(result["errors"]["base"], "cannot_connect")

        flow = self._flow(ScriptedApi(otp=RuntimeError("boom")))
        with self.assertLogs("lekkerladen_noha.config_flow", level="ERROR"):
            result = await flow.async_step_reauth_confirm({CONF_EMAIL: "a@b.co"})
        self.assertEqual(result["errors"]["base"], "unknown")
