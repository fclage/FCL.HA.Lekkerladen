"""Errors raised by the Lekkerladen API client."""


class LekkerladenError(Exception):
    """Base error."""


class LekkerladenAuthError(LekkerladenError):
    """Session missing, expired, or OTP rejected."""


class LekkerladenCannotConnect(LekkerladenError):
    """Network or unexpected HTTP failure."""
