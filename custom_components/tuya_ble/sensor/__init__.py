"""Sensor platform for tuya_ble."""

from __future__ import annotations

from types import MappingProxyType
from typing import TYPE_CHECKING

from ..const import PRODUCT_ID_SOIL_SENSOR
from .base import TuyaBleSensor
from .battery import TuyaBleBatterySensor
from .battery_state import TuyaBleBatteryStateSensor
from .soil_moisture import TuyaBleSoilMoistureSensor
from .temperature import TuyaBleTemperatureSensor

if TYPE_CHECKING:
    from collections.abc import Mapping

    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from ..data import TuyaBleConfigEntry

SENSORS_BY_PRODUCT: Mapping[str, tuple[type[TuyaBleSensor], ...]] = MappingProxyType(
    {
        PRODUCT_ID_SOIL_SENSOR: (
            TuyaBleSoilMoistureSensor,
            TuyaBleTemperatureSensor,
            TuyaBleBatterySensor,
            TuyaBleBatteryStateSensor,
        ),
    }
)

__all__ = [
    "SENSORS_BY_PRODUCT",
    "TuyaBleBatterySensor",
    "TuyaBleBatteryStateSensor",
    "TuyaBleSensor",
    "TuyaBleSoilMoistureSensor",
    "TuyaBleTemperatureSensor",
    "async_setup_entry",
]


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001 -- part of the signature Home Assistant calls
    entry: TuyaBleConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensors this product exposes."""
    runtime = entry.runtime_data
    async_add_entities(
        sensor(coordinator=runtime.coordinator)
        for sensor in SENSORS_BY_PRODUCT.get(runtime.product.product_id, ())
    )
