"""The coarse battery level reported alongside the percentage."""

from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import EntityCategory

from .base import BATTERY_STATES, TuyaBleSensor


class TuyaBleBatteryStateSensor(TuyaBleSensor):
    """
    The coarse battery level the device reports alongside the percentage.

    The datapoint is an enum, so the device sends the position within the
    product's own list of labels rather than the label itself.
    """

    _data_point_id = 14
    _attr_translation_key = "battery_state"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def options(self) -> list[str]:
        """Return the labels this datapoint can take."""
        return list(BATTERY_STATES)

    @property
    def native_value(self) -> str | None:
        """Return the label the reported position stands for."""
        data_point = self.data_point
        if data_point is None or not isinstance(data_point.value, int):
            return None
        if not 0 <= data_point.value < len(BATTERY_STATES):
            return None
        return BATTERY_STATES[data_point.value]
