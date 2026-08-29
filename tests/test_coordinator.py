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


async def test_one_silent_handshake_does_not_ask_for_credentials(
    hass, setup_integration, mock_client, resolvable_device
):
    from tuya_ble_sdk import TuyaBleHandshakeTimeoutError

    mock_client.async_read_data_points.side_effect = TuyaBleHandshakeTimeoutError(
        "hush"
    )

    with pytest.raises(TuyaBleHandshakeTimeoutError):
        await _coordinator(setup_integration)._async_poll_device(service_info())
    await hass.async_block_till_done()

    assert not hass.config_entries.flow.async_progress()


async def test_a_run_of_silent_handshakes_starts_a_reauth_flow(
    hass, setup_integration, mock_client, resolvable_device
):
    from tuya_ble_sdk import TuyaBleHandshakeTimeoutError

    from custom_components.tuya_ble.const import SILENT_HANDSHAKES_BEFORE_REAUTH

    mock_client.async_read_data_points.side_effect = TuyaBleHandshakeTimeoutError(
        "hush"
    )

    for _ in range(SILENT_HANDSHAKES_BEFORE_REAUTH):
        with pytest.raises(TuyaBleHandshakeTimeoutError):
            await _coordinator(setup_integration)._async_poll_device(service_info())
    await hass.async_block_till_done()

    assert any(
        flow["context"]["source"] == "reauth"
        for flow in hass.config_entries.flow.async_progress()
    )


async def test_a_successful_read_forgets_the_silence(
    hass, setup_integration, mock_client, resolvable_device
):
    from tuya_ble_sdk import TuyaBleHandshakeTimeoutError

    from custom_components.tuya_ble.const import SILENT_HANDSHAKES_BEFORE_REAUTH

    from .conftest import sample_data_points

    coordinator = _coordinator(setup_integration)
    for _ in range(SILENT_HANDSHAKES_BEFORE_REAUTH - 1):
        mock_client.async_read_data_points.side_effect = TuyaBleHandshakeTimeoutError(
            "h"
        )
        with pytest.raises(TuyaBleHandshakeTimeoutError):
            await coordinator._async_poll_device(service_info())

    mock_client.async_read_data_points.side_effect = None
    mock_client.async_read_data_points.return_value = sample_data_points()
    await coordinator._async_poll_device(service_info())

    assert coordinator._silent_handshakes == 0


async def test_a_plain_connection_failure_never_asks_for_credentials(
    hass, setup_integration, mock_client, resolvable_device
):
    mock_client.async_read_data_points.side_effect = TuyaBleConnectionError("asleep")

    for _ in range(5):
        with pytest.raises(TuyaBleConnectionError):
            await _coordinator(setup_integration)._async_poll_device(service_info())
    await hass.async_block_till_done()

    assert not hass.config_entries.flow.async_progress()


async def test_the_timer_reads_a_device_whose_advertisement_never_changes(
    hass, setup_integration, mock_client, resolvable_device
):
    """
    Home Assistant drops a repeated advertisement, so the callback fires once.

    Without the timer these sensors would be read only when the entry loads.
    """
    from unittest.mock import patch

    mock_client.async_read_data_points.reset_mock()

    with patch(
        "custom_components.tuya_ble.coordinator.async_last_service_info",
        return_value=service_info(),
    ):
        _coordinator(setup_integration).async_poll_if_due(None)
        await hass.async_block_till_done()

    assert mock_client.async_read_data_points.await_count == 1


async def test_the_timer_does_nothing_when_the_device_was_never_seen(
    hass, setup_integration, mock_client, resolvable_device
):
    from unittest.mock import patch

    mock_client.async_read_data_points.reset_mock()

    with patch(
        "custom_components.tuya_ble.coordinator.async_last_service_info",
        return_value=None,
    ):
        _coordinator(setup_integration).async_poll_if_due(None)
        await hass.async_block_till_done()

    assert mock_client.async_read_data_points.await_count == 0


async def test_the_timer_respects_the_interval(
    hass, setup_integration, mock_client, resolvable_device
):
    """A second tick inside the interval must not open a second connection."""
    from unittest.mock import patch

    mock_client.async_read_data_points.reset_mock()

    with patch(
        "custom_components.tuya_ble.coordinator.async_last_service_info",
        return_value=service_info(),
    ):
        _coordinator(setup_integration).async_poll_if_due(None)
        await hass.async_block_till_done()
        _coordinator(setup_integration).async_poll_if_due(None)
        await hass.async_block_till_done()

    assert mock_client.async_read_data_points.await_count == 1


async def test_a_device_with_nothing_to_report_keeps_the_last_values(
    hass, setup_integration, mock_client, resolvable_device
):
    """Reading nothing is normal for these sensors and must not blank them."""
    from .conftest import sample_data_points

    coordinator = _coordinator(setup_integration)
    mock_client.async_read_data_points.return_value = sample_data_points()
    coordinator.data = await coordinator._async_poll_device(service_info())

    mock_client.async_read_data_points.return_value = {}

    assert await coordinator._async_poll_device(service_info()) == sample_data_points()


async def test_a_partial_report_keeps_the_datapoints_it_left_out(
    hass, setup_integration, mock_client, resolvable_device
):
    """The device sends only what it has to say; the rest must not be blanked."""
    from tuya_ble_sdk import DataPoint, DataPointType

    from .conftest import sample_data_points

    coordinator = _coordinator(setup_integration)
    mock_client.async_read_data_points.return_value = sample_data_points()
    coordinator.data = await coordinator._async_poll_device(service_info())

    mock_client.async_read_data_points.return_value = {
        3: DataPoint(
            identifier=3, data_type=DataPointType.VALUE, value=51, timestamp=2.0
        )
    }
    merged = await coordinator._async_poll_device(service_info())

    assert merged[3].value == 51
    assert merged[15].value == 77
    assert set(merged) == {3, 5, 14, 15}


async def test_a_read_that_is_not_due_opens_no_connection(
    setup_integration, mock_client, resolvable_device
):
    """
    The debouncer runs a queued call without asking whether a read is due.

    A read that outlasts the check timer leaves one queued, so the interval has
    to be enforced here too or the device gets a second connection it never
    earned.
    """
    from bluetooth_data_tools import monotonic_time_coarse

    coordinator = _coordinator(setup_integration)
    coordinator.data = await coordinator._async_poll_device(service_info())
    coordinator._last_poll = monotonic_time_coarse()
    mock_client.async_read_data_points.reset_mock()

    kept = await coordinator._async_poll_device(service_info())

    assert mock_client.async_read_data_points.await_count == 0
    assert kept == coordinator.data


async def test_a_read_that_is_due_again_opens_a_connection(
    setup_integration, mock_client, resolvable_device
):
    from bluetooth_data_tools import monotonic_time_coarse

    coordinator = _coordinator(setup_integration)
    coordinator._last_poll = monotonic_time_coarse() - coordinator.poll_interval_seconds

    await coordinator._async_poll_device(service_info())

    assert mock_client.async_read_data_points.await_count == 1


async def test_a_failing_device_is_asked_less_and_less_often(
    setup_integration, mock_client, resolvable_device
):
    """A failed read holds a proxy connection slot; retrying at full rate starves it."""
    coordinator = _coordinator(setup_integration)
    mock_client.async_read_data_points.side_effect = TuyaBleConnectionError("asleep")
    interval = coordinator.poll_interval_seconds
    observed = []

    for _ in range(2):
        with pytest.raises(TuyaBleConnectionError):
            await coordinator._async_poll_device(service_info())
        observed.append(coordinator.poll_interval_seconds)

    assert observed == [interval * 2, interval * 4]


async def test_the_interval_never_grows_past_an_hour(
    setup_integration, mock_client, resolvable_device
):
    from custom_components.tuya_ble.const import MAX_POLL_INTERVAL_SECONDS

    coordinator = _coordinator(setup_integration)
    mock_client.async_read_data_points.side_effect = TuyaBleConnectionError("asleep")

    for _ in range(20):
        with pytest.raises(TuyaBleConnectionError):
            await coordinator._async_poll_device(service_info())

    assert coordinator.poll_interval_seconds == MAX_POLL_INTERVAL_SECONDS


async def test_a_successful_read_restores_the_configured_interval(
    setup_integration, mock_client, resolvable_device
):
    from .conftest import sample_data_points

    coordinator = _coordinator(setup_integration)
    interval = coordinator.poll_interval_seconds
    mock_client.async_read_data_points.side_effect = TuyaBleConnectionError("asleep")
    with pytest.raises(TuyaBleConnectionError):
        await coordinator._async_poll_device(service_info())

    mock_client.async_read_data_points.side_effect = None
    mock_client.async_read_data_points.return_value = sample_data_points()
    await coordinator._async_poll_device(service_info())

    assert coordinator.poll_interval_seconds == interval


async def test_a_rejected_local_key_also_widens_the_interval(
    hass, setup_integration, mock_client, resolvable_device
):
    coordinator = _coordinator(setup_integration)
    interval = coordinator.poll_interval_seconds
    mock_client.async_read_data_points.side_effect = TuyaBleAuthenticationError("no")

    with pytest.raises(TuyaBleAuthenticationError):
        await coordinator._async_poll_device(service_info())
    await hass.async_block_till_done()

    assert coordinator.poll_interval_seconds == interval * 2


async def test_a_silent_handshake_also_widens_the_interval(
    setup_integration, mock_client, resolvable_device
):
    from tuya_ble_sdk import TuyaBleHandshakeTimeoutError

    coordinator = _coordinator(setup_integration)
    interval = coordinator.poll_interval_seconds
    mock_client.async_read_data_points.side_effect = TuyaBleHandshakeTimeoutError("h")

    with pytest.raises(TuyaBleHandshakeTimeoutError):
        await coordinator._async_poll_device(service_info())

    assert coordinator.poll_interval_seconds == interval * 2


async def test_a_widened_interval_holds_back_the_timer(
    hass, setup_integration, mock_client, resolvable_device
):
    from unittest.mock import patch

    coordinator = _coordinator(setup_integration)
    mock_client.async_read_data_points.side_effect = TuyaBleConnectionError("asleep")

    with patch(
        "custom_components.tuya_ble.coordinator.async_last_service_info",
        return_value=service_info(),
    ):
        coordinator.async_poll_if_due(None)
        await hass.async_block_till_done()
    attempts = mock_client.async_read_data_points.await_count

    assert (
        coordinator._needs_poll(service_info(), coordinator._scan_interval_seconds)
        is False
    )
    assert attempts >= 1
