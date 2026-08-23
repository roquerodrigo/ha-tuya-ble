from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.config_entries import SOURCE_BLUETOOTH, SOURCE_USER
from homeassistant.data_entry_flow import FlowResultType
from tuya_ble_sdk import (
    CloudDevice,
    TuyaBleAuthenticationError,
    TuyaBleCloudError,
    TuyaBleConnectionError,
    TuyaBleProtocolError,
)

from custom_components.tuya_ble.const import DOMAIN

from .conftest import ADDRESS, DEVICE_ID, LOCAL_KEY, PRODUCT_ID, UUID, service_info

CREDENTIALS = {"device_id": DEVICE_ID, "local_key": LOCAL_KEY}
ACCOUNT = {
    "email": "someone@example.com",
    "password": "correct horse",
    "country_code": "55",
    "region": "us",
}
CLOUD_DEVICE = CloudDevice(
    device_id=DEVICE_ID,
    local_key=LOCAL_KEY,
    uuid=UUID,
    mac=ADDRESS.replace(":", ""),
    product_id=PRODUCT_ID,
    name="Soil sensor",
)


@pytest.fixture
def discovered():
    with patch(
        "custom_components.tuya_ble.config_flow.async_discovered_service_info",
        return_value=[service_info()],
    ) as discover:
        yield discover


@pytest.fixture
def account():
    """Patch the SDK client the account reader builds for one lookup."""
    with patch("custom_components.tuya_ble.account.TuyaBleCloudClient") as client_class:
        instance = MagicMock()
        instance.async_list_devices = AsyncMock(return_value=[CLOUD_DEVICE])
        client_class.return_value = instance
        yield instance


async def _start_bluetooth_flow(hass, info=None):
    return await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_BLUETOOTH}, data=info or service_info()
    )


async def _choose(hass, result, method):
    """Pick one of the two ways to hand over the credentials."""
    return await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": method}
    )


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_discovery_offers_both_ways_to_pair(hass):
    result = await _start_bluetooth_flow(hass)

    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "bluetooth_confirm"
    assert result["menu_options"] == ["account", "manual"]


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_typing_the_credentials_creates_the_entry(hass):
    result = await _start_bluetooth_flow(hass)
    result = await _choose(hass, result, "manual")

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], CREDENTIALS
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "SGS01 DDEEFF"
    assert result["data"] == {
        "address": ADDRESS,
        "product_id": "gvygg3m8",
        "uuid": UUID,
        "device_id": DEVICE_ID,
        "local_key": LOCAL_KEY,
    }


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_the_account_creates_the_entry(hass, account):
    result = await _start_bluetooth_flow(hass)
    result = await _choose(hass, result, "account")

    assert result["step_id"] == "account"

    result = await hass.config_entries.flow.async_configure(result["flow_id"], ACCOUNT)

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        "address": ADDRESS,
        "product_id": PRODUCT_ID,
        "uuid": UUID,
        "device_id": DEVICE_ID,
        "local_key": LOCAL_KEY,
    }


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_the_account_is_not_stored_on_the_entry(hass, account):
    result = await _start_bluetooth_flow(hass)
    result = await _choose(hass, result, "account")

    result = await hass.config_entries.flow.async_configure(result["flow_id"], ACCOUNT)

    assert "password" not in result["data"]
    assert "email" not in result["data"]


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_the_account_record_is_matched_by_address_when_the_uuid_differs(
    hass, account
):
    account.async_list_devices.return_value = [
        CloudDevice(
            device_id=DEVICE_ID,
            local_key=LOCAL_KEY,
            uuid="another uuid",
            mac="aa:bb:cc:dd:ee:ff",
            product_id=PRODUCT_ID,
            name="Soil sensor",
        )
    ]

    result = await _start_bluetooth_flow(hass)
    result = await _choose(hass, result, "account")
    result = await hass.config_entries.flow.async_configure(result["flow_id"], ACCOUNT)

    assert result["type"] is FlowResultType.CREATE_ENTRY


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_the_account_names_the_product_a_bound_device_hides(hass, account):
    result = await _start_bluetooth_flow(hass, service_info(obfuscated=True))
    result = await _choose(hass, result, "account")

    result = await hass.config_entries.flow.async_configure(result["flow_id"], ACCOUNT)

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["product_id"] == PRODUCT_ID


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_a_product_the_integration_does_not_support_is_refused(hass, account):
    account.async_list_devices.return_value = [
        CloudDevice(
            device_id=DEVICE_ID,
            local_key=LOCAL_KEY,
            uuid=UUID,
            mac=ADDRESS.replace(":", ""),
            product_id="unknown0",
            name="Something else",
        )
    ]

    result = await _start_bluetooth_flow(hass, service_info(obfuscated=True))
    result = await _choose(hass, result, "account")
    result = await hass.config_entries.flow.async_configure(result["flow_id"], ACCOUNT)

    assert result["errors"] == {"base": "unsupported_product"}


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_a_device_the_account_does_not_list_is_reported(hass, account):
    account.async_list_devices.return_value = []

    result = await _start_bluetooth_flow(hass)
    result = await _choose(hass, result, "account")
    result = await hass.config_entries.flow.async_configure(result["flow_id"], ACCOUNT)

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "device_not_in_account"}


@pytest.mark.parametrize(
    ("failure", "error"),
    [
        (TuyaBleAuthenticationError("rejected"), "invalid_auth"),
        (TuyaBleConnectionError("unreachable"), "cannot_connect"),
        (
            TuyaBleCloudError("login", "REQUEST_TOO_FREQUENTLY", "too frequent"),
            "account_busy",
        ),
        (TuyaBleProtocolError("nonsense"), "unknown"),
    ],
)
@pytest.mark.usefixtures("enable_custom_integrations")
async def test_a_failing_account_lookup_is_reported_on_the_form(
    hass, account, failure, error
):
    account.async_list_devices.side_effect = failure

    result = await _start_bluetooth_flow(hass)
    result = await _choose(hass, result, "account")
    result = await hass.config_entries.flow.async_configure(result["flow_id"], ACCOUNT)

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": error}


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_a_bound_device_is_asked_which_product_it_is(hass):
    result = await _start_bluetooth_flow(hass, service_info(obfuscated=True))
    result = await _choose(hass, result, "manual")

    assert result["type"] is FlowResultType.FORM
    assert "product_id" in result["data_schema"].schema


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_the_chosen_product_reaches_the_entry(hass):
    result = await _start_bluetooth_flow(hass, service_info(obfuscated=True))
    result = await _choose(hass, result, "manual")

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {**CREDENTIALS, "product_id": "gvygg3m8"}
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["product_id"] == "gvygg3m8"
    assert result["data"]["uuid"] == UUID


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_a_named_product_is_not_asked_for(hass):
    result = await _start_bluetooth_flow(hass)
    result = await _choose(hass, result, "manual")

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
    result = await _choose(hass, result, "manual")

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"device_id": "  ", "local_key": "abc"}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {
        "device_id": "invalid_device_id",
        "local_key": "invalid_local_key",
    }


@pytest.mark.usefixtures("enable_custom_integrations", "discovered")
async def test_the_picker_lists_the_devices_seen_nearby(hass):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"


@pytest.mark.usefixtures("enable_custom_integrations", "discovered")
async def test_a_device_picked_by_hand_creates_the_entry(hass):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"address": ADDRESS}
    )
    result = await _choose(hass, result, "manual")
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], CREDENTIALS
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_the_picker_aborts_when_nothing_is_around(hass):
    with patch(
        "custom_components.tuya_ble.config_flow.async_discovered_service_info",
        return_value=[],
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )

    assert result["reason"] == "no_devices_found"


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_the_picker_lists_a_bound_device_too(hass):
    with patch(
        "custom_components.tuya_ble.config_flow.async_discovered_service_info",
        return_value=[service_info(obfuscated=True)],
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )

    assert result["type"] is FlowResultType.FORM


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_the_picker_ignores_a_malformed_advertisement(hass):
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

    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "reauth_confirm"

    result = await _choose(hass, result, "manual")
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"device_id": DEVICE_ID, "local_key": "newlocalkey"}
    )
    await hass.async_block_till_done()

    assert result["reason"] == "reauth_successful"
    assert setup_integration.data["local_key"] == "newlocalkey"


async def test_reauth_offers_the_device_id_it_already_knows(hass, setup_integration):
    result = await setup_integration.start_reauth_flow(hass)

    result = await _choose(hass, result, "manual")

    assert result["data_schema"]({"local_key": LOCAL_KEY})["device_id"] == DEVICE_ID


async def test_reauth_reads_the_new_local_key_from_the_account(
    hass, setup_integration, account
):
    account.async_list_devices.return_value = [
        CloudDevice(
            device_id=DEVICE_ID,
            local_key="rotatedlocalkey",
            uuid=UUID,
            mac=ADDRESS.replace(":", ""),
            product_id=PRODUCT_ID,
            name="Soil sensor",
        )
    ]

    result = await setup_integration.start_reauth_flow(hass)
    result = await _choose(hass, result, "account")
    result = await hass.config_entries.flow.async_configure(result["flow_id"], ACCOUNT)
    await hass.async_block_till_done()

    assert result["reason"] == "reauth_successful"
    assert setup_integration.data["local_key"] == "rotatedlocalkey"


async def test_reauth_refuses_an_impossible_key(hass, setup_integration):
    result = await setup_integration.start_reauth_flow(hass)

    result = await _choose(hass, result, "manual")
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"device_id": DEVICE_ID, "local_key": "abc"}
    )

    assert result["errors"] == {"local_key": "invalid_local_key"}


async def test_reconfigure_replaces_the_credentials(hass, setup_integration):
    result = await setup_integration.start_reconfigure_flow(hass)

    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "reconfigure"

    result = await _choose(hass, result, "manual")
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"device_id": "eeeeeeeeeeeeeeee", "local_key": "anotherkey"}
    )
    await hass.async_block_till_done()

    assert result["reason"] == "reconfigure_successful"
    assert setup_integration.data["device_id"] == "eeeeeeeeeeeeeeee"


async def test_reconfigure_reads_the_credentials_from_the_account(
    hass, setup_integration, account
):
    account.async_list_devices.return_value = [
        CloudDevice(
            device_id="eeeeeeeeeeeeeeee",
            local_key=LOCAL_KEY,
            uuid=UUID,
            mac=ADDRESS.replace(":", ""),
            product_id=PRODUCT_ID,
            name="Soil sensor",
        )
    ]

    result = await setup_integration.start_reconfigure_flow(hass)
    result = await _choose(hass, result, "account")
    result = await hass.config_entries.flow.async_configure(result["flow_id"], ACCOUNT)
    await hass.async_block_till_done()

    assert result["reason"] == "reconfigure_successful"
    assert setup_integration.data["device_id"] == "eeeeeeeeeeeeeeee"


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_two_devices_of_one_product_get_distinct_titles(hass):
    """One entry is one physical device, so the model alone cannot name it."""
    titles = []
    for address in ("AA:BB:CC:DD:EE:FF", "AA:BB:CC:11:22:33"):
        result = await _start_bluetooth_flow(hass, service_info(address=address))
        result = await _choose(hass, result, "manual")
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], CREDENTIALS
        )
        titles.append(result["title"])

    assert titles[0] != titles[1]


@pytest.mark.usefixtures("enable_custom_integrations", "discovered")
async def test_the_picker_hides_a_device_already_configured(hass, config_entry):
    """The picker must not offer a device the user would only fail to add."""
    config_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "no_devices_found"
