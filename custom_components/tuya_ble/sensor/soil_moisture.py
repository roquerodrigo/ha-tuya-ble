"""Soil moisture, as the sensor's own percentage scale."""

from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import PERCENTAGE

from .base import TuyaBleSensor


class TuyaBleSoilMoistureSensor(TuyaBleSensor):
    """Soil moisture, as a percentage of the sensor's own scale."""

    _data_point_id = 3
    _attr_translation_key = "soil_moisture"
    _attr_device_class = SensorDeviceClass.MOISTURE
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> int | None:
        """Return the reported percentage."""
        data_point = self.data_point
        if data_point is None or not isinstance(data_point.value, int):
            return None
        return data_point.value
