from __future__ import annotations

import pytest
from homeassistant.config_entries import ConfigEntryState

from custom_components.tuya_ble.const import DOMAIN


async def test_the_entry_loads(setup_integration):
    assert setup_integration.state is ConfigEntryState.LOADED


async def test_the_runtime_data_carries_the_product(setup_integration):
    assert setup_integration.runtime_data.product.model == "SGS01"


async def test_the_entry_unloads(hass, setup_integration):
    assert await hass.config_entries.async_unload(setup_integration.entry_id)
    await hass.async_block_till_done()

    assert setup_integration.state is ConfigEntryState.NOT_LOADED


async def test_an_unknown_product_refuses_to_set_up(
    hass, mock_client, enable_custom_integrations
):
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "address": "AA:BB:CC:DD:EE:FF",
            "product_id": "unknown1",
            "uuid": "x" * 16,
            "device_id": "d" * 16,
            "local_key": "k" * 16,
        },
        unique_id="aa:bb:cc:dd:ee:ff",
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.SETUP_ERROR


async def test_changing_an_option_reloads_the_entry(hass, setup_integration):
    from homeassistant.const import CONF_SCAN_INTERVAL

    hass.config_entries.async_update_entry(
        setup_integration, options={CONF_SCAN_INTERVAL: 120}
    )
    await hass.async_block_till_done()

    assert setup_integration.state is ConfigEntryState.LOADED
    assert setup_integration.runtime_data.coordinator._scan_interval_seconds == 120


@pytest.mark.usefixtures("setup_integration")
async def test_the_device_is_registered_by_its_bluetooth_connection(hass):
    from homeassistant.helpers import device_registry as dr

    from .conftest import ADDRESS

    registry = dr.async_get(hass)
    device = registry.async_get_device(connections={(dr.CONNECTION_BLUETOOTH, ADDRESS)})

    assert device is not None
    assert device.manufacturer == "Tuya"
    assert device.model == "SGS01"
