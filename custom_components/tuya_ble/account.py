"""The Tuya account a device is bound to, asked for what the air never says."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import format_mac
from tuya_ble_sdk import TuyaBleCloudClient

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from tuya_ble_sdk import CloudDevice

    from .data import TuyaBleAccountCredentials


class TuyaBleAccount:
    """
    Reads one Tuya account, to spare the user copying credentials by hand.

    The device id and the local key a session needs are only known to the
    account that owns the device, and so is the product id of a device that is
    already bound. One login answers all three.
    """

    def __init__(
        self, hass: HomeAssistant, credentials: TuyaBleAccountCredentials
    ) -> None:
        """Build the SDK client for one account."""
        self._client = TuyaBleCloudClient(
            email=credentials["email"],
            password=credentials["password"],
            country_code=credentials["country_code"],
            region=credentials["region"],
            session=async_get_clientsession(hass),
        )

    async def async_device_at(self, uuid: str, address: str) -> CloudDevice | None:
        """
        Return what the account holds for the device seen at this address.

        The uuid decides: it is the one value the advertisement discloses and
        the account repeats. The address is the fallback for an account whose
        record predates the uuid it now broadcasts.
        """
        formatted = format_mac(address)
        for device in await self._client.async_list_devices():
            if device.uuid == uuid or (
                device.mac and format_mac(device.mac) == formatted
            ):
                return device
        return None
