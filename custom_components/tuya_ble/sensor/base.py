"""The datapoint-backed sensor every Tuya BLE sensor entity derives from."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.sensor import SensorEntity

from ..entity import TuyaBleEntity

if TYPE_CHECKING:
    from tuya_ble_sdk import DataPoint

TEMPERATURE_SCALE = 10
BATTERY_STATES: tuple[str, ...] = ("low", "middle", "high")


class TuyaBleSensor(TuyaBleEntity, SensorEntity):
    """
    Base for a sensor whose state is one datapoint of the device.

    Subclasses declare which datapoint they read and how to present it; the
    lookup and the "no report yet" case are handled once, here.
    """

    _data_point_id: int

    @property
    def unique_id(self) -> str:
        """Return an id derived from the address, which never changes."""
        return f"{self.coordinator.address}_{self._attr_translation_key}"

    @property
    def data_point(self) -> DataPoint | None:
        """Return this sensor's datapoint from the last report, if there was one."""
        data = self.coordinator.data
        if data is None:
            return None
        return data.get(self._data_point_id)
