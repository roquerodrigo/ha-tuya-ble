"""Remaining battery charge."""

from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import PERCENTAGE, EntityCategory

from .base import TuyaBleSensor


class TuyaBleBatterySensor(TuyaBleSensor):
    """Remaining battery charge."""

    _data_point_id = 15
    _attr_translation_key = "battery"
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self) -> int | None:
        """Return the reported percentage."""
        data_point = self.data_point
        if data_point is None or not isinstance(data_point.value, int):
            return None
        return data_point.value
