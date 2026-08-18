"""TuyaBleEntity base class."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, DOMAIN
from .coordinator import TuyaBleDataUpdateCoordinator


class TuyaBleEntity(CoordinatorEntity[TuyaBleDataUpdateCoordinator]):
    """Base entity for Tuya BLE."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info for the single integration device."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.config_entry.entry_id)},
            name="Tuya BLE",
            manufacturer="Tuya BLE",
        )
