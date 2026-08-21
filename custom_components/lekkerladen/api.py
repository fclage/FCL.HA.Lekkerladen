"""Async Lekkerladen HTTP client (Better Auth + Hono RPC)."""

from __future__ import annotations

import json
import logging
from typing import Any

from aiohttp import ClientError, ClientSession, ClientTimeout

from .const import (
    APP_URL,
    OTP_TYPE_SIGN_IN,
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
    SESSION_PAGE_LIMIT,
    USER_AGENT,
)
from .exceptions import LekkerladenAuthError, LekkerladenCannotConnect, LekkerladenError

_LOGGER = logging.getLogger(__name__)

_TIMEOUT = ClientTimeout(total=30)


class LekkerladenApi:
    """Talk to app.lekkerladen.com (auth) and api.lekkerladen.com (data)."""

    def __init__(self, session: ClientSession, token: str | None = None) -> None:
        self._session = session
        self._token = token

    @property
    def token(self) -> str | None:
        return self._token

    def set_token(self, token: str | None) -> None:
        self._token = token

    async def send_otp(self, email: str) -> None:
        """Request a 6-digit sign-in code by email."""
        payload = await self._request(
            "POST",
            PATH_SEND_OTP,
            json_body={"email": email, "type": OTP_TYPE_SIGN_IN},
            extra_headers={"X-Sign-Up-Flow": "false"},
            auth=False,
        )
        if isinstance(payload, dict) and payload.get("error"):
            raise LekkerladenAuthError(_error_message(payload) or "Could not send login code")

    async def sign_in(self, email: str, otp: str) -> dict[str, Any]:
        """Exchange email + OTP for a session token. Returns {token, user, session?}."""
        payload = await self._request(
            "POST",
            PATH_SIGN_IN,
            json_body={"email": email, "otp": otp},
            auth=False,
        )
        if not isinstance(payload, dict):
            raise LekkerladenAuthError("Unexpected sign-in response")
        if payload.get("error") or not payload.get("token"):
            raise LekkerladenAuthError(_error_message(payload) or "Invalid or expired code")
        self._token = payload["token"]
        return payload

    async def get_session(self) -> dict[str, Any] | None:
        """Return {session, user} or None if logged out."""
        payload = await self._request("GET", PATH_GET_SESSION)
        if payload is None:
            return None
        if not isinstance(payload, dict):
            raise LekkerladenCannotConnect("Unexpected session response")
        return payload

    async def get_chargers(self) -> list[dict[str, Any]]:
        payload = await self._request("GET", PATH_CHARGERS)
        return _list_field(payload, "chargers")

    async def get_accounts(self) -> list[dict[str, Any]]:
        payload = await self._request("GET", PATH_ACCOUNTS)
        return _list_field(payload, "accounts")

    async def get_profile(self) -> dict[str, Any] | None:
        payload = await self._request("GET", PATH_PROFILE)
        if isinstance(payload, dict):
            profile = payload.get("profile")
            if isinstance(profile, dict):
                return profile
            return payload
        return None

    async def get_ere_rate(self) -> dict[str, Any]:
        payload = await self._request("GET", PATH_ERE_RATE)
        return payload if isinstance(payload, dict) else {}

    async def get_contract(self) -> dict[str, Any]:
        payload = await self._request("GET", PATH_CONTRACT)
        return payload if isinstance(payload, dict) else {}

    async def get_sessions_monthly(self) -> list[dict[str, Any]]:
        payload = await self._request("GET", PATH_SESSIONS_MONTHLY)
        if isinstance(payload, dict):
            data = payload.get("data") or payload
            if isinstance(data, dict) and isinstance(data.get("months"), list):
                return data["months"]
        return []

    async def get_sessions(self, limit: int = SESSION_PAGE_LIMIT) -> list[dict[str, Any]]:
        payload = await self._request("POST", PATH_SESSIONS, json_body={"limit": limit})
        if isinstance(payload, dict):
            data = payload.get("data")
            if isinstance(data, list):
                return data
        return []

    async def fetch_dashboard(self) -> dict[str, Any]:
        """One poll: session + account/charger/session/rate payloads."""
        session = await self.get_session()
        if not session or not session.get("session"):
            raise LekkerladenAuthError("No active Lekkerladen session")
        return {
            "auth_session": session,
            "profile": await self.get_profile(),
            "chargers": await self.get_chargers(),
            "accounts": await self.get_accounts(),
            "monthly": await self.get_sessions_monthly(),
            "ere_rate": await self.get_ere_rate(),
            "contract": await self.get_contract(),
            "sessions": await self.get_sessions(),
        }

    async def _request(
        self,
        method: str,
        url: str,
        json_body: dict[str, Any] | None = None,
        extra_headers: dict[str, str] | None = None,
        auth: bool = True,
    ) -> Any:
        headers = {
            "Accept": "application/json",
            "Origin": APP_URL,
            "User-Agent": USER_AGENT,
        }
        if extra_headers:
            headers.update(extra_headers)
        if auth and self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        try:
            async with self._session.request(
                method,
                url,
                json=json_body,
                headers=headers,
                timeout=_TIMEOUT,
            ) as resp:
                text = await resp.text()
                payload = _maybe_json(text)
                if resp.status == 401:
                    raise LekkerladenAuthError(_error_message(payload) or "Unauthorized")
                if resp.status >= 400:
                    msg = _error_message(payload) or text or f"HTTP {resp.status}"
                    if resp.status in (400, 403) and _looks_like_auth(msg, payload):
                        raise LekkerladenAuthError(msg)
                    raise LekkerladenCannotConnect(msg)
                return payload
        except LekkerladenError:
            raise
        except TimeoutError as err:
            raise LekkerladenCannotConnect("Timeout talking to Lekkerladen") from err
        except ClientError as err:
            raise LekkerladenCannotConnect(str(err) or "Cannot connect to Lekkerladen") from err


def _maybe_json(text: str) -> Any:
    if not text:
        return None
    text = text.strip()
    if text in ("null", "undefined"):
        return None
    if text[:1] in "{[":
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text
    return text


def _error_message(payload: Any) -> str | None:
    if isinstance(payload, dict):
        err = payload.get("error")
        if isinstance(err, dict):
            msg = err.get("message") or err.get("code")
            if msg:
                return str(msg)
        if isinstance(err, str):
            return err
        for key in ("message", "code"):
            if payload.get(key):
                return str(payload[key])
    if isinstance(payload, str) and payload.strip():
        return payload.strip()
    return None


def _looks_like_auth(message: str, payload: Any) -> bool:
    blob = message.lower()
    if any(s in blob for s in ("otp", "invalid", "expired", "unauthorized", "session")):
        return True
    if isinstance(payload, dict) and str(payload.get("code", "")).upper() in {
        "INVALID_OTP",
        "OTP_EXPIRED",
        "UNAUTHORIZED",
        "VALIDATION_ERROR",
    }:
        return True
    return False


def _list_field(payload: Any, key: str) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []
