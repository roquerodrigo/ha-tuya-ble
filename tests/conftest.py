"""Shared fixtures for the Tuya BLE integration tests."""

from __future__ import annotations

from hashlib import md5
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bleak.backends.device import BLEDevice
from tuya_ble_sdk import DataPoint, DataPointType
from tuya_ble_sdk.crypto import encrypt
from tuya_ble_sdk.protocol import MANUFACTURER_DATA_IDENTIFIER, SERVICE_UUID

import custom_components.tuya_ble
import custom_components.tuya_ble.config_flow
import custom_components.tuya_ble.coordinator
import custom_components.tuya_ble.sensor  # noqa: F401

if TYPE_CHECKING:
    from collections.abc import Generator

pytest_plugins = "pytest_homeassistant_custom_component"

ADDRESS = "DC:23:51:E5:D1:3A"
PRODUCT_ID = "gvygg3m8"
UUID = "0123456789abcdef"
DEVICE_ID = "dddddddddddddddd"
LOCAL_KEY = "abcdef0123456789"


@pytest.fixture(autouse=True)
def expected_lingering_timers() -> bool:
    """
    Allow Home Assistant's Bluetooth scanner timers to outlive each test.

    ``enable_bluetooth`` loads the bluetooth integration, whose scanner
    schedules a periodic expiry timer that survives the integration unload.
    """
    return True


@pytest.fixture
def enable_custom_integrations(hass, enable_bluetooth) -> None:
    """Clear the custom-component cache and bring the bluetooth stack up."""
    from homeassistant.loader import DATA_CUSTOM_COMPONENTS

    hass.data.pop(DATA_CUSTOM_COMPONENTS, None)


def encrypted_uuid(product_id: str = PRODUCT_ID, uuid: str = UUID) -> bytes:
    """Encrypt a uuid the way a Tuya BLE advertisement carries it."""
    key = md5(product_id.encode()).digest()
    return encrypt(key, key, uuid.encode())


def service_info(
    *,
    address: str = ADDRESS,
    product_id: str | None = PRODUCT_ID,
    with_manufacturer_data: bool = True,
    connectable: bool = True,
):
    """Build the advertisement Home Assistant hands to the integration."""
    from bluetooth_data_tools import monotonic_time_coarse
    from habluetooth import BluetoothServiceInfoBleak

    service_data = (
        {SERVICE_UUID: b"\x00" + product_id.encode()} if product_id is not None else {}
    )
    manufacturer_data = (
        {
            MANUFACTURER_DATA_IDENTIFIER: bytes([0x80, 3, 0, 0, 1, 0])
            + encrypted_uuid(product_id or PRODUCT_ID)
        }
        if with_manufacturer_data
        else {}
    )
    return BluetoothServiceInfoBleak(
        name="TY",
        address=address,
        rssi=-67,
        manufacturer_data=manufacturer_data,
        service_data=service_data,
        service_uuids=[SERVICE_UUID],
        source="proxy",
        device=BLEDevice(address=address, name="TY", details={}),
        advertisement=None,
        connectable=connectable,
        time=monotonic_time_coarse(),
        tx_power=None,
    )


def inject_advertisement(hass, info=None) -> None:
    """Feed one advertisement into Home Assistant's Bluetooth manager."""
    from homeassistant.components.bluetooth import async_get_advertisement_callback

    async_get_advertisement_callback(hass)(info or service_info())


def sample_data_points() -> dict[int, DataPoint]:
    """A full report from the soil sensor."""
    return {
        3: DataPoint(
            identifier=3, data_type=DataPointType.VALUE, value=42, timestamp=1.0
        ),
        5: DataPoint(
            identifier=5, data_type=DataPointType.VALUE, value=260, timestamp=1.0
        ),
        14: DataPoint(
            identifier=14, data_type=DataPointType.ENUM, value=1, timestamp=1.0
        ),
        15: DataPoint(
            identifier=15, data_type=DataPointType.VALUE, value=77, timestamp=1.0
        ),
    }


@pytest.fixture
def mock_client() -> Generator[MagicMock]:
    """Patch the SDK client the coordinator builds for every poll."""
    with patch("custom_components.tuya_ble.coordinator.TuyaBleClient") as client_class:
        instance = MagicMock()
        instance.async_read_data_points = AsyncMock(return_value=sample_data_points())
        client_class.return_value = instance
        yield instance


@pytest.fixture
def config_entry():
    """A config entry describing the soil sensor."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.tuya_ble.const import DOMAIN

    return MockConfigEntry(
        domain=DOMAIN,
        data={
            "address": ADDRESS,
            "product_id": PRODUCT_ID,
            "uuid": UUID,
            "device_id": DEVICE_ID,
            "local_key": LOCAL_KEY,
        },
        unique_id=ADDRESS.lower(),
        title="Soil sensor",
    )


@pytest.fixture
async def setup_integration(
    hass, config_entry, mock_client, enable_custom_integrations
):
    """Set the integration up with a stubbed device."""
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    return config_entry
