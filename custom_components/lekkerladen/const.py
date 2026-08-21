"""Constants for the Lekkerladen integration."""

from datetime import timedelta
from typing import Final

DOMAIN: Final = "lekkerladen"
ATTRIBUTION: Final = "Data provided by Lekkerladen"

APP_URL: Final = "https://app.lekkerladen.com"
API_URL: Final = "https://api.lekkerladen.com"
AUTH_BASE: Final = f"{APP_URL}/auth"

# Better Auth (email OTP plugin)
PATH_SEND_OTP: Final = f"{AUTH_BASE}/email-otp/send-verification-otp"
PATH_SIGN_IN: Final = f"{AUTH_BASE}/sign-in/email-otp"
PATH_GET_SESSION: Final = f"{AUTH_BASE}/get-session"

PATH_CHARGERS: Final = f"{API_URL}/api/chargers"
PATH_SESSIONS: Final = f"{API_URL}/api/sessions"
PATH_SESSIONS_MONTHLY: Final = f"{API_URL}/api/sessions/monthly"
PATH_ERE_RATE: Final = f"{API_URL}/api/ere-rate"
PATH_PROFILE: Final = f"{API_URL}/api/profiles/current"
PATH_CONTRACT: Final = f"{API_URL}/api/contracts/current"
PATH_ACCOUNTS: Final = f"{API_URL}/api/accounts"

VERSION: Final = "0.1.0"
USER_AGENT: Final = f"HomeAssistant-Lekkerladen/{VERSION}"
OTP_TYPE_SIGN_IN: Final = "sign-in"
OTP_LENGTH: Final = 6

CONF_TOKEN: Final = "token"
CONF_USER_ID: Final = "user_id"
CONF_EXPIRES_AT: Final = "expires_at"

DEFAULT_SCAN_INTERVAL: Final = timedelta(minutes=15)
SESSION_PAGE_LIMIT: Final = 20

AMSTERDAM_TZ: Final = "Europe/Amsterdam"
