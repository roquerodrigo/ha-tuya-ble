from __future__ import annotations

import copy
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest

if TYPE_CHECKING:
    from collections.abc import Generator

    from homeassistant.core import HomeAssistant

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def expected_lingering_timers() -> bool:
    """
    Allow Home Assistant's Bluetooth scanner timers to outlive each test.

    ``enable_bluetooth`` loads the bluetooth integration, whose scanner
    schedules a periodic expiry timer that survives the integration unload.
    """
    return True


@pytest.fixture
def enable_custom_integrations(hass: HomeAssistant, enable_bluetooth: None) -> None:
    """Clear the custom-component cache and bring the bluetooth stack up."""
    from homeassistant.loader import DATA_CUSTOM_COMPONENTS

    hass.data.pop(DATA_CUSTOM_COMPONENTS, None)


SAMPLE_PAYLOAD = {
    "userId": 1,
    "id": 1,
    "title": "sunt aut facere repellat provident",
    "body": "quia et suscipit suscipit",
}


@pytest.fixture
def sample_payload() -> dict:
    return copy.deepcopy(SAMPLE_PAYLOAD)


@pytest.fixture
def mock_api_client(sample_payload: dict) -> Generator:
    with patch("custom_components.tuya_ble.TuyaBleApiClient") as mock_class:
        instance = mock_class.return_value
        instance.async_get_data = AsyncMock(return_value=sample_payload)
        instance.async_set_title = AsyncMock(return_value=None)
        yield instance


@pytest.fixture
async def setup_integration(hass, mock_api_client, enable_custom_integrations):
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.tuya_ble.const import DOMAIN

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"username": "user", "password": "pass"},
        unique_id="user",
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry
