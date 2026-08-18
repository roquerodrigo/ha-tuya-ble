"""Custom types for tuya_ble."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING

from .config_data import TuyaBleConfigData
from .diagnostics_entry import TuyaBleDiagnosticsEntry
from .diagnostics_payload import TuyaBleDiagnosticsPayload
from .options_data import TuyaBleOptionsData
from .runtime import TuyaBleData

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from tuya_ble_sdk import DataPoint


type JsonPrimitive = str | int | float | bool | None
type JsonValue = JsonPrimitive | list[JsonValue] | Mapping[str, JsonValue]
type JsonObject = Mapping[str, JsonValue]

type TuyaBleDataPoints = Mapping[int, DataPoint]
type TuyaBleConfigEntry = ConfigEntry[TuyaBleData]

__all__ = [
    "JsonObject",
    "JsonPrimitive",
    "JsonValue",
    "TuyaBleConfigData",
    "TuyaBleConfigEntry",
    "TuyaBleData",
    "TuyaBleDataPoints",
    "TuyaBleDiagnosticsEntry",
    "TuyaBleDiagnosticsPayload",
    "TuyaBleOptionsData",
]
