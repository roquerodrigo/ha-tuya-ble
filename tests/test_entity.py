from __future__ import annotations

import pytest
from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH

from .conftest import ADDRESS, inject_advertisement


def _sensor(entry):
    from custom_components.tuya_ble.sensor import TuyaBleSoilMoistureSensor

    return TuyaBleSoilMoistureSensor(coordinator=entry.runtime_data.coordinator)


async def test_the_device_info_identifies_the_bluetooth_connection(setup_integration):
    device_info = _sensor(setup_integration).device_info

    assert device_info["connections"] == {(CONNECTION_BLUETOOTH, ADDRESS)}
    assert device_info["manufacturer"] == "Tuya"
    assert device_info["model"] == "SGS01"
    assert device_info["translation_key"] == "soil_sensor"
    assert "name" not in device_info


async def test_entities_carry_the_device_name(setup_integration):
    assert _sensor(setup_integration)._attr_has_entity_name is True


@pytest.mark.usefixtures("setup_integration")
async def test_entities_are_unavailable_until_the_device_is_seen(hass):
    assert hass.states.get("sensor.soil_sensor_battery").state == "unavailable"


@pytest.mark.usefixtures("setup_integration", "mock_client")
async def test_an_advertisement_makes_the_entities_available(hass):
    inject_advertisement(hass)
    await hass.async_block_till_done()

    assert hass.states.get("sensor.soil_sensor_battery").state != "unavailable"
