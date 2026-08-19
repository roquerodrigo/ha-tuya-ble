"""Bluetooth coordinator for tuya_ble."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.bluetooth import (
    BluetoothChange,
    BluetoothScanningMode,
    async_ble_device_from_address,
    async_last_service_info,
)
from homeassistant.components.bluetooth.active_update_coordinator import (
    ActiveBluetoothDataUpdateCoordinator,
)
from homeassistant.core import CoreState, callback
from tuya_ble_sdk import (
    TuyaBleAuthenticationError,
    TuyaBleClient,
    TuyaBleHandshakeTimeoutError,
)

from .const import LOGGER, SILENT_HANDSHAKES_BEFORE_REAUTH

if TYPE_CHECKING:
    from datetime import datetime

    from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
    from homeassistant.core import HomeAssistant
    from tuya_ble_sdk import TuyaBleCredentials

    from .data import TuyaBleConfigEntry, TuyaBleDataPoints


class TuyaBleDataUpdateCoordinator(
    ActiveBluetoothDataUpdateCoordinator["TuyaBleDataPoints | None"]
):
    """
    Reads one Tuya BLE device, driven by its advertisements and by a timer.

    Advertisements alone are not enough. Home Assistant drops an advertisement
    whose payload is byte-identical to the one before it, and these sensors
    broadcast a constant payload — so the callback fires once, when the entry
    loads, and then never again. ``async_poll_if_due`` closes that gap by
    replaying the last advertisement on a timer.

    The advertisement path is still worth keeping: it is what reads the device
    the moment it comes back after being out of range. ``scan_interval``
    remains the minimum spacing between two reads, whichever path asks for one.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: TuyaBleConfigEntry,
        credentials: TuyaBleCredentials,
        scan_interval_seconds: float,
    ) -> None:
        """Initialize."""
        self.config_entry = config_entry
        self._credentials = credentials
        self._scan_interval_seconds = scan_interval_seconds
        self._silent_handshakes = 0
        super().__init__(
            hass=hass,
            logger=LOGGER,
            address=config_entry.data["address"],
            mode=BluetoothScanningMode.PASSIVE,
            needs_poll_method=self._needs_poll,
            poll_method=self._async_poll_device,
            connectable=True,
        )

    @callback
    def async_poll_if_due(self, _now: datetime) -> None:
        """
        Offer the last advertisement to the poll logic again.

        The device is not woken here: this only re-runs the decision Home
        Assistant would have run on an advertisement, so ``_needs_poll`` stays
        the single place that decides whether a read is due.
        """
        service_info = async_last_service_info(
            self.hass, self.address, connectable=True
        )
        if service_info is None:
            return
        self._async_handle_bluetooth_event(service_info, BluetoothChange.ADVERTISEMENT)

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
    ) -> TuyaBleDataPoints | None:
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
            self._start_reauth()
            raise
        except TuyaBleHandshakeTimeoutError:
            self._count_silent_handshake()
            raise
        self._silent_handshakes = 0
        if not data_points:
            LOGGER.debug("%s: nothing new to report", self.address)
            return self.data
        LOGGER.debug("%s: read datapoints %s", self.address, sorted(data_points))
        return data_points

    def _count_silent_handshake(self) -> None:
        """
        Treat a run of ignored handshakes as the device refusing the local key.

        The device never says "wrong key": it simply drops the one frame that
        key protects. One occurrence proves nothing — a busy device drops
        frames too — so the reauth flow only opens once the silence is
        consistent, and any successful read resets the count.
        """
        self._silent_handshakes += 1
        if self._silent_handshakes < SILENT_HANDSHAKES_BEFORE_REAUTH:
            LOGGER.warning(
                "%s: the device ignored the handshake (%s in a row)",
                self.address,
                self._silent_handshakes,
            )
            return
        LOGGER.error(
            "%s: the device ignored %s handshakes in a row; the local key is "
            "probably no longer valid",
            self.address,
            self._silent_handshakes,
        )
        self._start_reauth()

    def _start_reauth(self) -> None:
        """Ask the user for credentials again, without losing the last values."""
        self._silent_handshakes = 0
        self.config_entry.async_start_reauth(self.hass)
