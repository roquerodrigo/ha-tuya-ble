"""Soil temperature, reported in tenths of a degree."""

from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfTemperature

from .base import TEMPERATURE_SCALE, TuyaBleSensor


class TuyaBleTemperatureSensor(TuyaBleSensor):
    """Soil temperature; the device reports tenths of a degree."""

    _data_point_id = 5
    _attr_translation_key = "temperature"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 1

    @property
    def native_value(self) -> float | None:
        """Return the reported temperature in whole degrees."""
        data_point = self.data_point
        if data_point is None or not isinstance(data_point.value, int):
            return None
        return data_point.value / TEMPERATURE_SCALE
