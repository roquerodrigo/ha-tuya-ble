"""TuyaBleEntity base class."""

from __future__ import annotations

from homeassistant.components.bluetooth.passive_update_coordinator import (
    PassiveBluetoothCoordinatorEntity,
)
from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH, DeviceInfo

from .const import MANUFACTURER
from .coordinator import TuyaBleDataUpdateCoordinator


class TuyaBleEntity(PassiveBluetoothCoordinatorEntity[TuyaBleDataUpdateCoordinator]):
    """Base entity for one Tuya BLE device."""

    _attr_has_entity_name = True

    @property
    def device_info(self) -> DeviceInfo:
        """Describe the physical device every entity of this entry belongs to."""
        product = self.coordinator.config_entry.runtime_data.product
        return DeviceInfo(
            connections={(CONNECTION_BLUETOOTH, self.coordinator.address)},
            translation_key=product.translation_key,
            manufacturer=MANUFACTURER,
            model=product.model,
        )
