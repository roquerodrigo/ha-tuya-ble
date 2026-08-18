from __future__ import annotations

from unittest.mock import patch

import pytest
from homeassistant.config_entries import SOURCE_BLUETOOTH, SOURCE_USER
from homeassistant.data_entry_flow import FlowResultType

from custom_components.tuya_ble.const import DOMAIN

from .conftest import ADDRESS, DEVICE_ID, LOCAL_KEY, service_info

CREDENTIALS = {"device_id": DEVICE_ID, "local_key": LOCAL_KEY}


@pytest.fixture
def discovered():
    with patch(
        "custom_components.tuya_ble.config_flow.async_discovered_service_info",
        return_value=[service_info()],
    ) as discover:
        yield discover


async def _start_bluetooth_flow(hass, info=None):
    return await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_BLUETOOTH}, data=info or service_info()
    )


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_discovery_asks_for_the_credentials(hass):
    result = await _start_bluetooth_flow(hass)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "bluetooth_confirm"


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_discovery_creates_the_entry(hass):
    result = await _start_bluetooth_flow(hass)

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], CREDENTIALS
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        "address": ADDRESS,
        "product_id": "gvygg3m8",
        "uuid": "0123456789abcdef",
        "device_id": DEVICE_ID,
        "local_key": LOCAL_KEY,
    }


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_a_bound_device_is_asked_which_product_it_is(hass):
    result = await _start_bluetooth_flow(hass, service_info(obfuscated=True))

    assert result["type"] is FlowResultType.FORM
    assert "product_id" in result["data_schema"].schema


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_the_chosen_product_reaches_the_entry(hass):
    result = await _start_bluetooth_flow(hass, service_info(obfuscated=True))

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {**CREDENTIALS, "product_id": "gvygg3m8"}
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["product_id"] == "gvygg3m8"
    assert result["data"]["uuid"] == "0123456789abcdef"


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_a_named_product_is_not_asked_for(hass):
    result = await _start_bluetooth_flow(hass)

    assert "product_id" not in result["data_schema"].schema


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_an_advertisement_without_a_uuid_is_rejected(hass):
    result = await _start_bluetooth_flow(
        hass, service_info(with_manufacturer_data=False)
    )

    assert result["reason"] == "not_supported"


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_a_malformed_advertisement_is_rejected(hass):
    info = service_info()
    info.service_data["0000a201-0000-1000-8000-00805f9b34fb"] = b"\x00\xff"

    result = await _start_bluetooth_flow(hass, info)

    assert result["reason"] == "not_supported"


async def test_a_device_already_configured_is_not_offered_again(
    hass, config_entry, enable_custom_integrations
):
    config_entry.add_to_hass(hass)

    result = await _start_bluetooth_flow(hass)

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_empty_credentials_are_refused(hass):
    result = await _start_bluetooth_flow(hass)

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"device_id": "  ", "local_key": "abc"}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {
        "device_id": "invalid_device_id",
        "local_key": "invalid_local_key",
    }


@pytest.mark.usefixtures("enable_custom_integrations", "discovered")
async def test_the_manual_flow_lists_the_devices_seen_nearby(hass):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"


@pytest.mark.usefixtures("enable_custom_integrations", "discovered")
async def test_the_manual_flow_creates_the_entry(hass):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"address": ADDRESS}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], CREDENTIALS
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_the_manual_flow_aborts_when_nothing_is_around(hass):
    with patch(
        "custom_components.tuya_ble.config_flow.async_discovered_service_info",
        return_value=[],
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )

    assert result["reason"] == "no_devices_found"


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_the_manual_flow_lists_a_bound_device_too(hass):
    with patch(
        "custom_components.tuya_ble.config_flow.async_discovered_service_info",
        return_value=[service_info(obfuscated=True)],
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )

    assert result["type"] is FlowResultType.FORM


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_the_manual_flow_ignores_a_malformed_advertisement(hass):
    info = service_info()
    info.service_data["0000a201-0000-1000-8000-00805f9b34fb"] = b"\x00\xff"

    with patch(
        "custom_components.tuya_ble.config_flow.async_discovered_service_info",
        return_value=[info],
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )

    assert result["reason"] == "no_devices_found"


async def test_reauth_replaces_the_local_key(hass, setup_integration):
    result = await setup_integration.start_reauth_flow(hass)

    assert result["step_id"] == "reauth_confirm"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"device_id": DEVICE_ID, "local_key": "newlocalkey"}
    )
    await hass.async_block_till_done()

    assert result["reason"] == "reauth_successful"
    assert setup_integration.data["local_key"] == "newlocalkey"


async def test_reauth_refuses_an_impossible_key(hass, setup_integration):
    result = await setup_integration.start_reauth_flow(hass)

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"device_id": DEVICE_ID, "local_key": "abc"}
    )

    assert result["errors"] == {"local_key": "invalid_local_key"}


async def test_reconfigure_replaces_the_credentials(hass, setup_integration):
    result = await setup_integration.start_reconfigure_flow(hass)

    assert result["step_id"] == "reconfigure"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"device_id": "eeeeeeeeeeeeeeee", "local_key": "anotherkey"}
    )
    await hass.async_block_till_done()

    assert result["reason"] == "reconfigure_successful"
    assert setup_integration.data["device_id"] == "eeeeeeeeeeeeeeee"
