from __future__ import annotations

import pytest
from homeassistant.const import STATE_UNKNOWN
from tuya_ble_sdk import DataPoint, DataPointType

from .conftest import inject_advertisement, sample_data_points

ENTITIES = (
    "sensor.soil_sensor_soil_moisture",
    "sensor.soil_sensor_temperature",
    "sensor.soil_sensor_battery",
    "sensor.soil_sensor_battery_state",
)


async def _publish(hass, mock_client, data_points):
    """Let the device report `data_points` the next time it advertises."""
    mock_client.async_read_data_points.return_value = data_points
    inject_advertisement(hass)
    await hass.async_block_till_done()


@pytest.mark.usefixtures("setup_integration")
async def test_every_sensor_of_the_product_is_created(hass):
    for entity_id in ENTITIES:
        assert hass.states.get(entity_id) is not None


async def test_states_come_from_the_report(hass, setup_integration, mock_client):
    await _publish(hass, mock_client, sample_data_points())

    assert hass.states.get("sensor.soil_sensor_soil_moisture").state == "42"
    assert hass.states.get("sensor.soil_sensor_temperature").state == "26.0"
    assert hass.states.get("sensor.soil_sensor_battery").state == "77"
    assert hass.states.get("sensor.soil_sensor_battery_state").state == "middle"


async def test_sensors_are_unknown_before_the_first_report(hass, setup_integration):
    setup_integration.runtime_data.coordinator._available = True
    setup_integration.runtime_data.coordinator.async_update_listeners()
    await hass.async_block_till_done()

    for entity_id in ENTITIES:
        assert hass.states.get(entity_id).state == STATE_UNKNOWN


async def test_a_missing_datapoint_reads_unknown(hass, setup_integration, mock_client):
    await _publish(hass, mock_client, {})

    for entity_id in ENTITIES:
        assert hass.states.get(entity_id).state == STATE_UNKNOWN


async def test_a_datapoint_of_the_wrong_type_reads_unknown(
    hass, setup_integration, mock_client
):
    await _publish(
        hass,
        mock_client,
        {
            identifier: DataPoint(
                identifier=identifier,
                data_type=DataPointType.RAW,
                value=b"\x01",
                timestamp=1.0,
            )
            for identifier in (3, 5, 14, 15)
        },
    )

    for entity_id in ENTITIES:
        assert hass.states.get(entity_id).state == STATE_UNKNOWN


async def test_a_battery_state_outside_the_scale_reads_unknown(
    hass, setup_integration, mock_client
):
    await _publish(
        hass,
        mock_client,
        {
            14: DataPoint(
                identifier=14, data_type=DataPointType.ENUM, value=9, timestamp=1.0
            )
        },
    )

    assert hass.states.get("sensor.soil_sensor_battery_state").state == STATE_UNKNOWN


async def test_the_battery_state_offers_every_label(
    hass, setup_integration, mock_client
):
    await _publish(hass, mock_client, sample_data_points())

    state = hass.states.get("sensor.soil_sensor_battery_state")
    assert state.attributes["options"] == ["low", "middle", "high"]


@pytest.mark.usefixtures("setup_integration")
async def test_unique_ids_are_derived_from_the_address(hass):
    from homeassistant.helpers import entity_registry as er

    registry = er.async_get(hass)
    unique_ids = {
        registry.async_get(entity_id).unique_id
        for entity_id in ENTITIES
        if registry.async_get(entity_id) is not None
    }

    assert unique_ids == {
        "DC:23:51:E5:D1:3A_soil_moisture",
        "DC:23:51:E5:D1:3A_temperature",
        "DC:23:51:E5:D1:3A_battery",
        "DC:23:51:E5:D1:3A_battery_state",
    }


@pytest.mark.usefixtures("setup_integration")
async def test_a_product_without_a_table_entry_creates_nothing(hass):
    from custom_components.tuya_ble.sensor import SENSORS_BY_PRODUCT

    assert SENSORS_BY_PRODUCT.get("nothing") is None
