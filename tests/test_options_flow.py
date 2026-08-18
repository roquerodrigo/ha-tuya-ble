from __future__ import annotations

from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.data_entry_flow import FlowResultType


async def test_the_form_offers_the_current_interval(hass, setup_integration):
    result = await hass.config_entries.options.async_init(setup_integration.entry_id)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"


async def test_saving_an_interval_stores_it(hass, setup_integration):
    result = await hass.config_entries.options.async_init(setup_integration.entry_id)

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_SCAN_INTERVAL: 300}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert setup_integration.options[CONF_SCAN_INTERVAL] == 300


async def test_the_stored_interval_reaches_the_coordinator(hass, setup_integration):
    result = await hass.config_entries.options.async_init(setup_integration.entry_id)
    await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_SCAN_INTERVAL: 300}
    )
    await hass.async_block_till_done()

    assert setup_integration.runtime_data.coordinator._scan_interval_seconds == 300
