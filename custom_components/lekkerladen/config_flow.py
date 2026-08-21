"""Config flow: email → OTP email → 6-digit code."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import SOURCE_REAUTH, ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_EMAIL
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import LekkerladenApi
from .const import CONF_EXPIRES_AT, CONF_TOKEN, CONF_USER_ID, DOMAIN, OTP_LENGTH
from .exceptions import LekkerladenAuthError, LekkerladenCannotConnect

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): str,
    }
)
STEP_OTP_SCHEMA = vol.Schema(
    {
        vol.Required("otp"): str,
    }
)


class LekkerladenConfigFlow(ConfigFlow, domain=DOMAIN):
    """Set up Lekkerladen with email OTP (same as the web app)."""

    VERSION = 1

    def __init__(self) -> None:
        self._email: str | None = None
        self._api: LekkerladenApi | None = None

    def _client(self) -> LekkerladenApi:
        if self._api is None:
            self._api = LekkerladenApi(async_get_clientsession(self.hass))
        return self._api

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            email = user_input[CONF_EMAIL].strip().lower()
            if "@" not in email or "." not in email.split("@")[-1]:
                errors["base"] = "invalid_email"
            else:
                self._email = email
                try:
                    await self._client().send_otp(email)
                except LekkerladenAuthError:
                    errors["base"] = "otp_send_failed"
                except LekkerladenCannotConnect:
                    errors["base"] = "cannot_connect"
                except Exception:
                    _LOGGER.exception("Unexpected error sending Lekkerladen OTP")
                    errors["base"] = "unknown"
                else:
                    return await self.async_step_otp()

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_SCHEMA,
            errors=errors,
        )

    async def async_step_otp(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            otp = "".join(ch for ch in user_input.get("otp", "") if ch.isdigit())
            if len(otp) != OTP_LENGTH:
                errors["base"] = "invalid_otp"
            else:
                try:
                    signed = await self._client().sign_in(self._email or "", otp)
                    session = await self._client().get_session()
                except LekkerladenAuthError:
                    errors["base"] = "invalid_otp"
                except LekkerladenCannotConnect:
                    errors["base"] = "cannot_connect"
                except Exception:
                    _LOGGER.exception("Unexpected error during Lekkerladen sign-in")
                    errors["base"] = "unknown"
                else:
                    return await self._async_finish(signed, session)

        return self.async_show_form(
            step_id="otp",
            data_schema=STEP_OTP_SCHEMA,
            errors=errors,
            description_placeholders={"email": self._email or ""},
        )

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> ConfigFlowResult:
        self._email = (entry_data.get(CONF_EMAIL) or "").strip().lower()
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            email = (user_input.get(CONF_EMAIL) or self._email or "").strip().lower()
            self._email = email
            try:
                await self._client().send_otp(email)
            except LekkerladenAuthError:
                errors["base"] = "otp_send_failed"
            except LekkerladenCannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error sending Lekkerladen reauth OTP")
                errors["base"] = "unknown"
            else:
                return await self.async_step_otp()

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {vol.Required(CONF_EMAIL, default=self._email or ""): str}
            ),
            errors=errors,
        )

    async def _async_finish(
        self, signed: dict[str, Any], session: dict[str, Any] | None
    ) -> ConfigFlowResult:
        user = (session or {}).get("user") or signed.get("user") or {}
        sess = (session or {}).get("session") or {}
        user_id = user.get("id")
        email = user.get("email") or self._email
        token = signed.get("token") or sess.get("token")
        if not user_id or not token:
            return self.async_abort(reason="unknown")

        await self.async_set_unique_id(str(user_id))
        if self.source == SOURCE_REAUTH:
            self._abort_if_unique_id_mismatch(reason="wrong_account")
            return self.async_update_reload_and_abort(
                self._get_reauth_entry(),
                data_updates={
                    CONF_EMAIL: email,
                    CONF_TOKEN: token,
                    CONF_USER_ID: str(user_id),
                    CONF_EXPIRES_AT: sess.get("expiresAt"),
                },
            )

        self._abort_if_unique_id_configured()
        title = email or "Lekkerladen"
        return self.async_create_entry(
            title=str(title),
            data={
                CONF_EMAIL: email,
                CONF_TOKEN: token,
                CONF_USER_ID: str(user_id),
                CONF_EXPIRES_AT: sess.get("expiresAt"),
            },
        )
