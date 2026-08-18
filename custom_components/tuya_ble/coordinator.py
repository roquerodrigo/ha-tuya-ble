"""Bluetooth coordinator for tuya_ble."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.bluetooth import (
    BluetoothScanningMode,
    async_ble_device_from_address,
)
from homeassistant.components.bluetooth.active_update_coordinator import (
    ActiveBluetoothDataUpdateCoordinator,
)
from homeassistant.core import CoreState
from tuya_ble_sdk import TuyaBleAuthenticationError, TuyaBleClient

from .const import LOGGER

if TYPE_CHECKING:
    from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
    from homeassistant.core import HomeAssistant
    from tuya_ble_sdk import TuyaBleCredentials

    from .data import TuyaBleConfigEntry, TuyaBleDataPoints


class TuyaBleDataUpdateCoordinator(
    ActiveBluetoothDataUpdateCoordinator["TuyaBleDataPoints | None"]
):
    """
    Reads one Tuya BLE device whenever it announces that it is awake.

    A timer-driven coordinator would mostly poll a device that is asleep: these
    sensors advertise every few minutes and only listen for a moment
    afterwards. Home Assistant therefore drives the poll from the
    advertisement, and ``scan_interval`` becomes the minimum spacing between
    two reads rather than a schedule.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: TuyaBleConfigEntry,
        credentials: TuyaBleCredentials,
        scan_interval_seconds: int,
    ) -> None:
        """Initialize."""
        self.config_entry = config_entry
        self._credentials = credentials
        self._scan_interval_seconds = scan_interval_seconds
        super().__init__(
            hass=hass,
            logger=LOGGER,
            address=config_entry.data["address"],
            mode=BluetoothScanningMode.PASSIVE,
            needs_poll_method=self._needs_poll,
            poll_method=self._async_poll_device,
            connectable=True,
        )

    def _needs_poll(
        self,
        service_info: BluetoothServiceInfoBleak,
        seconds_since_last_poll: float | None,
    ) -> bool:
        """Decide whether this advertisement is worth waking a connection for."""
        if self.hass.state is not CoreState.running:
            return False
        if (
            seconds_since_last_poll is not None
            and seconds_since_last_poll < self._scan_interval_seconds
        ):
            return False
        return (
            async_ble_device_from_address(
                self.hass, service_info.device.address, connectable=True
            )
            is not None
        )

    async def _async_poll_device(
        self, service_info: BluetoothServiceInfoBleak
    ) -> TuyaBleDataPoints:
        """Run one whole session against the device that just advertised."""
        device = (
            async_ble_device_from_address(
                self.hass, service_info.device.address, connectable=True
            )
            or service_info.device
        )
        try:
            data_points = await TuyaBleClient(
                device, self._credentials
            ).async_read_data_points()
        except TuyaBleAuthenticationError as exception:
            LOGGER.error("Failed to authenticate with the device: %s", exception)
            self.config_entry.async_start_reauth(self.hass)
            raise
        LOGGER.debug("%s: read datapoints %s", self.address, sorted(data_points))
        return data_points
