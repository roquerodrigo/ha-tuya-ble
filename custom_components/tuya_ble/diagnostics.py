"""Diagnostics support for tuya_ble."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from homeassistant.components.bluetooth import async_last_service_info
from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_DEVICE_ID

from .const import CONF_LOCAL_KEY, CONF_UUID

if TYPE_CHECKING:
    from collections.abc import Mapping

    from homeassistant.core import HomeAssistant

    from .data import (
        TuyaBleConfigEntry,
        TuyaBleDiagnosticsEntry,
        TuyaBleDiagnosticsPayload,
    )

TO_REDACT: frozenset[str] = frozenset({CONF_DEVICE_ID, CONF_LOCAL_KEY, CONF_UUID})


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: TuyaBleConfigEntry,
) -> TuyaBleDiagnosticsPayload:
    """Return diagnostics for a config entry."""
    redacted_data = cast(
        "Mapping[str, str]",
        async_redact_data(dict(entry.data), set(TO_REDACT)),
    )
    redacted_options = cast(
        "Mapping[str, str | int]",
        async_redact_data(dict(entry.options), set(TO_REDACT)),
    )
    diagnostics_entry: TuyaBleDiagnosticsEntry = {
        "title": entry.title,
        "version": entry.version,
        "domain": entry.domain,
        "data": redacted_data,
        "options": redacted_options,
    }
    return {
        "entry": diagnostics_entry,
        "advertisement": _advertisement(hass, entry),
        "data_points": _data_points(entry),
    }


def _advertisement(
    hass: HomeAssistant, entry: TuyaBleConfigEntry
) -> Mapping[str, str | int | bool | None] | None:
    """
    Summarize the last advertisement Home Assistant saw from this device.

    The raw payload is left out: it carries the encrypted device uuid, which is
    the identifier the rest of the dump redacts.
    """
    service_info = async_last_service_info(
        hass, entry.data["address"], connectable=True
    )
    if service_info is None:
        return None
    return {
        "name": service_info.name,
        "rssi": service_info.rssi,
        "source": service_info.source,
        "connectable": service_info.connectable,
    }


def _data_points(
    entry: TuyaBleConfigEntry,
) -> Mapping[str, str | int | float | bool | None]:
    """Render the last report in a form a JSON dump can carry."""
    data = entry.runtime_data.coordinator.data
    if data is None:
        return {}
    return {
        str(identifier): (
            data_point.value.hex()
            if isinstance(data_point.value, bytes)
            else data_point.value
        )
        for identifier, data_point in data.items()
    }
