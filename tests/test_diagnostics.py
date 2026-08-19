from __future__ import annotations

import pytest

from custom_components.tuya_ble.diagnostics import (
    async_get_config_entry_diagnostics,
)

from .conftest import ADDRESS, inject_advertisement


async def test_secrets_are_redacted(hass, setup_integration):
    payload = await async_get_config_entry_diagnostics(hass, setup_integration)

    assert payload["entry"]["data"]["local_key"] == "**REDACTED**"
    assert payload["entry"]["data"]["device_id"] == "**REDACTED**"
    assert payload["entry"]["data"]["uuid"] == "**REDACTED**"


async def test_the_address_and_the_product_are_kept(hass, setup_integration):
    payload = await async_get_config_entry_diagnostics(hass, setup_integration)

    assert payload["entry"]["data"]["address"] == ADDRESS
    assert payload["entry"]["data"]["product_id"] == "gvygg3m8"


async def test_the_last_advertisement_is_summarized(hass, setup_integration):
    inject_advertisement(hass)
    await hass.async_block_till_done()

    payload = await async_get_config_entry_diagnostics(hass, setup_integration)

    assert payload["advertisement"] == {
        "name": "TY",
        "rssi": -67,
        "source": "proxy",
        "connectable": True,
    }


async def test_no_advertisement_is_reported_as_none(hass, setup_integration):
    payload = await async_get_config_entry_diagnostics(hass, setup_integration)

    assert payload["advertisement"] is None


async def test_the_last_report_is_included(hass, setup_integration, mock_client):
    inject_advertisement(hass)
    await hass.async_block_till_done()

    payload = await async_get_config_entry_diagnostics(hass, setup_integration)

    assert payload["data_points"] == {"3": 42, "5": 260, "14": 1, "15": 77}


async def test_an_empty_report_is_an_empty_mapping(hass, setup_integration):
    payload = await async_get_config_entry_diagnostics(hass, setup_integration)

    assert payload["data_points"] == {}


async def test_raw_datapoints_are_rendered_as_hexadecimal(
    hass, setup_integration, mock_client
):
    from tuya_ble_sdk import DataPoint, DataPointType

    mock_client.async_read_data_points.return_value = {
        7: DataPoint(
            identifier=7,
            data_type=DataPointType.RAW,
            value=b"\xde\xad",
            timestamp=1.0,
        )
    }
    inject_advertisement(hass)
    await hass.async_block_till_done()

    payload = await async_get_config_entry_diagnostics(hass, setup_integration)

    assert payload["data_points"] == {"7": "dead"}


@pytest.mark.usefixtures("setup_integration")
def test_the_redaction_list_is_a_frozenset():
    from custom_components.tuya_ble.diagnostics import TO_REDACT

    assert isinstance(TO_REDACT, frozenset)
