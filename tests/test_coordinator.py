from __future__ import annotations

from unittest.mock import patch

import pytest
from homeassistant.core import CoreState
from tuya_ble_sdk import TuyaBleAuthenticationError, TuyaBleConnectionError

from .conftest import ADDRESS, service_info


def _coordinator(entry):
    return entry.runtime_data.coordinator


@pytest.fixture
def resolvable_device():
    with patch(
        "custom_components.tuya_ble.coordinator.async_ble_device_from_address"
    ) as resolve:
        resolve.return_value = service_info().device
        yield resolve


async def test_the_first_advertisement_is_worth_a_poll(
    setup_integration, resolvable_device
):
    assert _coordinator(setup_integration)._needs_poll(service_info(), None) is True


async def test_a_second_advertisement_within_the_interval_is_not(
    setup_integration, resolvable_device
):
    assert _coordinator(setup_integration)._needs_poll(service_info(), 10.0) is False


async def test_an_advertisement_after_the_interval_is(
    setup_integration, resolvable_device
):
    assert _coordinator(setup_integration)._needs_poll(service_info(), 1000.0) is True


async def test_an_unconnectable_device_is_not_polled(setup_integration):
    with patch(
        "custom_components.tuya_ble.coordinator.async_ble_device_from_address",
        return_value=None,
    ):
        assert (
            _coordinator(setup_integration)._needs_poll(service_info(), None) is False
        )


async def test_a_stopping_instance_is_not_polled(
    hass, setup_integration, resolvable_device
):
    hass.set_state(CoreState.stopping)

    assert _coordinator(setup_integration)._needs_poll(service_info(), None) is False


async def test_a_poll_returns_the_report(
    setup_integration, mock_client, resolvable_device
):
    data_points = await _coordinator(setup_integration)._async_poll_device(
        service_info()
    )

    assert set(data_points) == {3, 5, 14, 15}


async def test_a_poll_uses_the_stored_credentials(
    setup_integration, mock_client, resolvable_device
):
    with patch("custom_components.tuya_ble.coordinator.TuyaBleClient") as client_class:
        client_class.return_value.async_read_data_points = (
            mock_client.async_read_data_points
        )
        await _coordinator(setup_integration)._async_poll_device(service_info())

    credentials = client_class.call_args.args[1]
    assert credentials.device_id == "dddddddddddddddd"
    assert credentials.uuid == "0123456789abcdef"


async def test_a_rejected_local_key_starts_a_reauth_flow(
    hass, setup_integration, mock_client, resolvable_device
):
    mock_client.async_read_data_points.side_effect = TuyaBleAuthenticationError("no")

    with pytest.raises(TuyaBleAuthenticationError):
        await _coordinator(setup_integration)._async_poll_device(service_info())
    await hass.async_block_till_done()

    assert any(
        flow["context"]["source"] == "reauth"
        for flow in hass.config_entries.flow.async_progress()
    )


async def test_a_connection_failure_is_left_to_the_coordinator(
    setup_integration, mock_client, resolvable_device
):
    mock_client.async_read_data_points.side_effect = TuyaBleConnectionError("asleep")

    with pytest.raises(TuyaBleConnectionError):
        await _coordinator(setup_integration)._async_poll_device(service_info())


async def test_the_address_is_the_configured_one(setup_integration):
    assert _coordinator(setup_integration).address == ADDRESS


async def test_an_advertisement_drives_a_poll(hass, setup_integration, mock_client):
    from .conftest import inject_advertisement

    inject_advertisement(hass)
    await hass.async_block_till_done()

    assert mock_client.async_read_data_points.await_count == 1
    assert set(_coordinator(setup_integration).data) == {3, 5, 14, 15}
