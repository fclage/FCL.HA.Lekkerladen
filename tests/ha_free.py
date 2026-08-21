"""Import the HA-free Lekkerladen modules without loading Home Assistant."""

from __future__ import annotations

import sys
import types
from pathlib import Path

_PKG = "lekkerladen_noha"
_ROOT = Path(__file__).resolve().parents[1] / "custom_components" / "lekkerladen"


def _stub_aiohttp() -> None:
    if "aiohttp" in sys.modules:
        return
    aio = types.ModuleType("aiohttp")

    class ClientError(Exception):
        pass

    class ClientTimeout:
        def __init__(self, total: float | None = None) -> None:
            self.total = total

    class ClientSession:
        pass

    aio.ClientError = ClientError
    aio.ClientTimeout = ClientTimeout
    aio.ClientSession = ClientSession
    sys.modules["aiohttp"] = aio


def _install() -> None:
    _stub_aiohttp()
    if _PKG in sys.modules:
        return
    pkg = types.ModuleType(_PKG)
    pkg.__path__ = [str(_ROOT)]
    sys.modules[_PKG] = pkg


_install()
