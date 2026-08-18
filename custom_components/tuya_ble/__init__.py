"""Tuya BLE integration for Home Assistant."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING, cast

from homeassistant.const import CONF_SCAN_INTERVAL, Platform
from homeassistant.exceptions import ConfigEntryError
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.loader import async_get_loaded_integration
from tuya_ble_sdk import TuyaBleCredentials

from .const import DEFAULT_SCAN_INTERVAL_SECONDS, POLL_CHECK_INTERVAL_SECONDS
from .coordinator import TuyaBleDataUpdateCoordinator
from .data import TuyaBleData
from .products import product_for

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .data import TuyaBleConfigData, TuyaBleConfigEntry

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TuyaBleConfigEntry,
) -> bool:
    """Set up Tuya BLE from a config entry."""
    config = cast("TuyaBleConfigData", entry.data)
    product = product_for(config["product_id"])
    if product is None:
        message = f"Product {config['product_id']} is no longer supported"
        raise ConfigEntryError(message)

    coordinator = TuyaBleDataUpdateCoordinator(
        hass=hass,
        config_entry=entry,
        credentials=TuyaBleCredentials(
            uuid=config["uuid"],
            device_id=config["device_id"],
            local_key=config["local_key"],
        ),
        scan_interval_seconds=int(
            entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_SECONDS),
        ),
    )
    entry.runtime_data = TuyaBleData(
        coordinator=coordinator,
        product=product,
        integration=async_get_loaded_integration(hass, entry.domain),
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(coordinator.async_start())
    entry.async_on_unload(
        async_track_time_interval(
            hass,
            coordinator.async_poll_if_due,
            timedelta(seconds=POLL_CHECK_INTERVAL_SECONDS),
        )
    )
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: TuyaBleConfigEntry,
) -> bool:
    """Handle removal of an entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_reload_entry(
    hass: HomeAssistant,
    entry: TuyaBleConfigEntry,
) -> None:
    """Reload config entry."""
    await hass.config_entries.async_reload(entry.entry_id)
