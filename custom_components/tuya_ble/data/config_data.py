"""Typed shape of the device identity persisted on the config entry."""

from __future__ import annotations

from typing import TypedDict


class TuyaBleConfigData(TypedDict):
    """
    What one config entry stores about one Tuya BLE device.

    The address and the product id come from the advertisement; the device id
    and the local key come from the user's Tuya account and are the only
    secrets involved.
    """

    address: str
    product_id: str
    uuid: str
    device_id: str
    local_key: str
