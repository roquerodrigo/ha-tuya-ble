"""Sensor platform for tuya_ble."""

from __future__ import annotations

from types import MappingProxyType
from typing import TYPE_CHECKING

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfTemperature

from .entity import TuyaBleEntity

if TYPE_CHECKING:
    from collections.abc import Mapping

    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback
    from tuya_ble_sdk import DataPoint

    from .data import TuyaBleConfigEntry

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


SENSORS_BY_PRODUCT: Mapping[str, tuple[type[TuyaBleSensor], ...]] = MappingProxyType(
    {
        "gvygg3m8": (
            TuyaBleSoilMoistureSensor,
            TuyaBleTemperatureSensor,
            TuyaBleBatterySensor,
            TuyaBleBatteryStateSensor,
        ),
    }
)


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
