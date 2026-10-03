"""Import Lekkerladen without a Home Assistant install.

Stubs are enough to construct entities, the coordinator, and the config flow.
They are not a Home Assistant runtime.
"""

from __future__ import annotations

import importlib.util
import sys
import types
from dataclasses import dataclass
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


def _stub_voluptuous() -> None:
    if "voluptuous" in sys.modules:
        return
    vol = types.ModuleType("voluptuous")

    class Required:
        def __init__(self, key: object, *args: object, **kwargs: object) -> None:
            self.key = key
            self.default = kwargs.get("default")

    class Schema:
        def __init__(self, schema: object, *args: object, **kwargs: object) -> None:
            self.schema = schema

    vol.Required = Required
    vol.Schema = Schema
    sys.modules["voluptuous"] = vol


def _module(name: str, *, package: bool = False) -> types.ModuleType:
    mod = types.ModuleType(name)
    mod.__package__ = name if package else name.rpartition(".")[0]
    if package:
        mod.__path__ = []
    sys.modules[name] = mod
    return mod


def _stub_homeassistant() -> None:
    if "homeassistant" in sys.modules:
        return

    ha = _module("homeassistant", package=True)
    const = _module("homeassistant.const")
    core = _module("homeassistant.core")
    config_entries = _module("homeassistant.config_entries")
    exceptions = _module("homeassistant.exceptions")
    helpers = _module("homeassistant.helpers", package=True)
    update_coordinator = _module("homeassistant.helpers.update_coordinator")
    device_registry = _module("homeassistant.helpers.device_registry")
    entity = _module("homeassistant.helpers.entity")
    entity_platform = _module("homeassistant.helpers.entity_platform")
    aiohttp_client = _module("homeassistant.helpers.aiohttp_client")
    components = _module("homeassistant.components", package=True)
    diagnostics = _module("homeassistant.components.diagnostics")
    sensor = _module("homeassistant.components.sensor")
    binary_sensor = _module("homeassistant.components.binary_sensor")

    class Platform:
        BINARY_SENSOR = "binary_sensor"
        SENSOR = "sensor"

    class UnitOfEnergy:
        KILO_WATT_HOUR = "kWh"

    const.Platform = Platform
    const.CONF_EMAIL = "email"
    const.CURRENCY_EURO = "EUR"
    const.UnitOfEnergy = UnitOfEnergy

    class HomeAssistant:
        pass

    core.HomeAssistant = HomeAssistant

    class ConfigEntry:
        def __class_getitem__(cls, item: object) -> type:
            return cls

    class ConfigFlow:
        def __init_subclass__(cls, domain: str | None = None, **kwargs: object) -> None:
            super().__init_subclass__(**kwargs)
            cls.domain = domain

        def async_show_form(
            self,
            step_id: str,
            data_schema: object = None,
            errors: dict[str, str] | None = None,
            description_placeholders: dict[str, str] | None = None,
        ) -> dict[str, object]:
            form = {
                "type": "form",
                "step_id": step_id,
                "errors": errors or {},
                "schema": data_schema,
                "description_placeholders": description_placeholders,
            }
            self.last_form = form
            return form

        def async_abort(self, reason: str) -> dict[str, str]:
            self.abort_reason = reason
            return {"type": "abort", "reason": reason}

        async def async_set_unique_id(self, unique_id: str) -> None:
            self.unique_id = unique_id

        def _abort_if_unique_id_mismatch(self, reason: str = "wrong_account") -> None:
            self.mismatch_reason = reason

        def _abort_if_unique_id_configured(self) -> None:
            self.checked_configured = True

        def _get_reauth_entry(self) -> object:
            return getattr(self, "reauth_entry", None)

        def async_update_reload_and_abort(
            self, entry: object, data_updates: dict[str, object]
        ) -> dict[str, object]:
            self.reauth_updates = data_updates
            self.reauth_target = entry
            return {"type": "abort", "reason": "reauth_successful", "data": data_updates}

        def async_create_entry(self, title: str, data: dict[str, object]) -> dict[str, object]:
            created = {"type": "create_entry", "title": title, "data": data}
            self.created = created
            return created

    config_entries.ConfigEntry = ConfigEntry
    config_entries.ConfigFlow = ConfigFlow
    config_entries.ConfigFlowResult = dict
    config_entries.SOURCE_REAUTH = "reauth"

    class ConfigEntryAuthFailed(Exception):
        pass

    exceptions.ConfigEntryAuthFailed = ConfigEntryAuthFailed

    class UpdateFailed(Exception):
        pass

    class DataUpdateCoordinator:
        def __init__(
            self,
            hass: object,
            logger: object,
            *,
            name: str,
            update_interval: object,
            config_entry: object = None,
        ) -> None:
            self.hass = hass
            self.logger = logger
            self.name = name
            self.update_interval = update_interval
            self.config_entry = config_entry
            self.data = None

        async def async_config_entry_first_refresh(self) -> None:
            self.data = await self._async_update_data()

        def __class_getitem__(cls, item: object) -> type:
            return cls

    class CoordinatorEntity:
        def __init__(self, coordinator: object) -> None:
            self.coordinator = coordinator

        def __class_getitem__(cls, item: object) -> type:
            return cls

    update_coordinator.DataUpdateCoordinator = DataUpdateCoordinator
    update_coordinator.UpdateFailed = UpdateFailed
    update_coordinator.CoordinatorEntity = CoordinatorEntity

    class DeviceInfo:
        def __init__(self, **kwargs: object) -> None:
            self.__dict__.update(kwargs)

    device_registry.DeviceInfo = DeviceInfo

    class EntityCategory:
        DIAGNOSTIC = "diagnostic"

    entity.EntityCategory = EntityCategory
    entity_platform.AddEntitiesCallback = object

    def async_get_clientsession(hass: object) -> object:
        return getattr(hass, "session", None)

    aiohttp_client.async_get_clientsession = async_get_clientsession

    def async_redact_data(data: object, to_redact: set[str]) -> object:
        if isinstance(data, dict):
            redacted: dict[object, object] = {}
            for key, value in data.items():
                if key in to_redact:
                    redacted[key] = "**REDACTED**"
                else:
                    redacted[key] = async_redact_data(value, to_redact)
            return redacted
        if isinstance(data, list):
            return [async_redact_data(item, to_redact) for item in data]
        return data

    diagnostics.async_redact_data = async_redact_data

    @dataclass(frozen=True, kw_only=True)
    class SensorEntityDescription:
        key: str
        translation_key: str | None = None
        native_unit_of_measurement: str | None = None
        device_class: str | None = None
        state_class: str | None = None
        suggested_display_precision: int | None = None
        icon: str | None = None
        entity_category: str | None = None

    class SensorDeviceClass:
        ENERGY = "energy"
        MONETARY = "monetary"
        TIMESTAMP = "timestamp"

    class SensorStateClass:
        TOTAL = "total"

    class SensorEntity:
        pass

    sensor.SensorEntityDescription = SensorEntityDescription
    sensor.SensorDeviceClass = SensorDeviceClass
    sensor.SensorStateClass = SensorStateClass
    sensor.SensorEntity = SensorEntity

    @dataclass(frozen=True, kw_only=True)
    class BinarySensorEntityDescription:
        key: str
        translation_key: str | None = None
        device_class: str | None = None
        icon: str | None = None
        entity_category: str | None = None

    class BinarySensorDeviceClass:
        CONNECTIVITY = "connectivity"
        PROBLEM = "problem"

    class BinarySensorEntity:
        pass

    binary_sensor.BinarySensorEntityDescription = BinarySensorEntityDescription
    binary_sensor.BinarySensorDeviceClass = BinarySensorDeviceClass
    binary_sensor.BinarySensorEntity = BinarySensorEntity

    ha.const = const
    ha.core = core
    ha.config_entries = config_entries
    ha.exceptions = exceptions
    ha.helpers = helpers
    ha.components = components
    helpers.update_coordinator = update_coordinator
    helpers.device_registry = device_registry
    helpers.entity = entity
    helpers.entity_platform = entity_platform
    helpers.aiohttp_client = aiohttp_client
    components.diagnostics = diagnostics
    components.sensor = sensor
    components.binary_sensor = binary_sensor


def _load_package_init(pkg: types.ModuleType) -> None:
    """Run the integration __init__ into the pre-registered package."""
    if getattr(pkg, "async_setup_entry", None) is not None:
        return
    spec = importlib.util.spec_from_file_location(
        _PKG,
        _ROOT / "__init__.py",
        submodule_search_locations=[str(_ROOT)],
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load the lekkerladen package")
    spec.loader.exec_module(pkg)


def _install() -> None:
    _stub_aiohttp()
    _stub_voluptuous()
    _stub_homeassistant()
    pkg = sys.modules.get(_PKG)
    if pkg is None:
        pkg = types.ModuleType(_PKG)
        pkg.__package__ = _PKG
        pkg.__path__ = [str(_ROOT)]
        sys.modules[_PKG] = pkg
    _load_package_init(pkg)


_install()
