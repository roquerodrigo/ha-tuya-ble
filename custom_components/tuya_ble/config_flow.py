"""Config flow for tuya_ble."""

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict, cast

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components.bluetooth import async_discovered_service_info
from homeassistant.const import CONF_ADDRESS, CONF_DEVICE_ID
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.device_registry import format_mac
from tuya_ble_sdk import TuyaBleError, parse_advertisement

from .const import CONF_LOCAL_KEY, DOMAIN, LOGGER, MIN_LOCAL_KEY_LENGTH
from .options_flow import TuyaBleOptionsFlow
from .products import product_for

if TYPE_CHECKING:
    from collections.abc import Mapping

    from homeassistant.components.bluetooth import BluetoothServiceInfoBleak

    from .data import TuyaBleConfigData, TuyaBleConfigEntry
    from .products import TuyaBleProduct


class TuyaBleCredentialsInput(TypedDict):
    """The two values the pairing handshake needs from the user."""

    device_id: str
    local_key: str


def _credentials_schema(
    defaults: TuyaBleCredentialsInput | None = None,
) -> vol.Schema:
    """Build the device id / local key schema, optionally pre-filled."""
    return vol.Schema(
        {
            vol.Required(
                CONF_DEVICE_ID,
                default=defaults["device_id"] if defaults else vol.UNDEFINED,
            ): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT),
            ),
            vol.Required(CONF_LOCAL_KEY): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD),
            ),
        },
    )


class TuyaBleFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """
    Config flow for Tuya BLE.

    The credentials are not tried against the device while the flow is open:
    these sensors sleep between advertisements, so a connection attempt would
    time out far more often than it would catch a typo. A wrong local key
    surfaces on the first poll instead, as a reauth prompt.
    """

    VERSION = 1

    _address: str
    _product: TuyaBleProduct
    _uuid: str

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: TuyaBleConfigEntry,  # noqa: ARG004
    ) -> TuyaBleOptionsFlow:
        """Return the options flow handler."""
        return TuyaBleOptionsFlow()

    async def async_step_bluetooth(
        self,
        discovery_info: BluetoothServiceInfoBleak,
    ) -> config_entries.ConfigFlowResult:
        """Handle a device discovered by the Bluetooth integration."""
        await self.async_set_unique_id(format_mac(discovery_info.address))
        self._abort_if_unique_id_configured()
        if not self._adopt(discovery_info):
            return self.async_abort(reason="not_supported")
        self.context["title_placeholders"] = {"name": self._product.name}
        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self,
        user_input: TuyaBleCredentialsInput | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Ask for the credentials that pair this device."""
        errors: dict[str, str] = {}

        if user_input is not None:
            errors = _validate(user_input)
            if not errors:
                return self.async_create_entry(
                    title=self._product.name,
                    data=cast(
                        "TuyaBleConfigData",
                        {
                            CONF_ADDRESS: self._address,
                            "product_id": self._product.product_id,
                            "uuid": self._uuid,
                            CONF_DEVICE_ID: user_input["device_id"].strip(),
                            CONF_LOCAL_KEY: user_input["local_key"].strip(),
                        },
                    ),
                )

        return self.async_show_form(
            step_id="bluetooth_confirm",
            data_schema=_credentials_schema(user_input),
            description_placeholders={"name": self._product.name},
            errors=errors,
        )

    async def async_step_user(
        self,
        user_input: Mapping[str, str] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Let the user pick one of the supported devices seen nearby."""
        candidates = self._candidates()
        if not candidates:
            return self.async_abort(reason="no_devices_found")

        if user_input is not None:
            discovery_info = candidates[user_input[CONF_ADDRESS]]
            await self.async_set_unique_id(
                format_mac(discovery_info.address), raise_on_progress=False
            )
            self._abort_if_unique_id_configured()
            if not self._adopt(discovery_info):
                return self.async_abort(reason="not_supported")
            return await self.async_step_bluetooth_confirm()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ADDRESS): vol.In(
                        {
                            address: f"{info.name} ({address})"
                            for address, info in candidates.items()
                        }
                    )
                }
            ),
        )

    async def async_step_reauth(
        self,
        entry_data: Mapping[str, str],  # noqa: ARG002
    ) -> config_entries.ConfigFlowResult:
        """Trigger reauth when the device rejects the stored local key."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self,
        user_input: TuyaBleCredentialsInput | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Prompt for a fresh local key and update the entry."""
        return await self._async_update_credentials("reauth_confirm", user_input)

    async def async_step_reconfigure(
        self,
        user_input: TuyaBleCredentialsInput | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Allow editing the credentials of an existing entry."""
        return await self._async_update_credentials("reconfigure", user_input)

    async def _async_update_credentials(
        self,
        step_id: str,
        user_input: TuyaBleCredentialsInput | None,
    ) -> config_entries.ConfigFlowResult:
        """Re-ask for the credentials of an entry that already exists."""
        errors: dict[str, str] = {}
        entry = (
            self._get_reauth_entry()
            if step_id == "reauth_confirm"
            else self._get_reconfigure_entry()
        )
        existing = cast("TuyaBleConfigData", entry.data)

        if user_input is not None:
            errors = _validate(user_input)
            if not errors:
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates={
                        CONF_DEVICE_ID: user_input["device_id"].strip(),
                        CONF_LOCAL_KEY: user_input["local_key"].strip(),
                    },
                )

        return self.async_show_form(
            step_id=step_id,
            data_schema=_credentials_schema(
                user_input
                or TuyaBleCredentialsInput(
                    device_id=existing["device_id"], local_key=""
                )
            ),
            errors=errors,
        )

    def _adopt(self, discovery_info: BluetoothServiceInfoBleak) -> bool:
        """Read the advertisement and keep it, unless the product is unknown."""
        try:
            advertisement = parse_advertisement(
                discovery_info.service_data, discovery_info.manufacturer_data
            )
        except TuyaBleError as exception:
            LOGGER.debug("Failed to read the advertisement: %s", exception)
            return False
        product = product_for(advertisement.product_id)
        if product is None or advertisement.uuid is None:
            return False
        self._address = discovery_info.address
        self._product = product
        self._uuid = advertisement.uuid
        return True

    def _candidates(self) -> dict[str, BluetoothServiceInfoBleak]:
        """Return the supported devices seen nearby that are not set up yet."""
        configured = self._async_current_ids()
        return {
            discovery_info.address: discovery_info
            for discovery_info in async_discovered_service_info(
                self.hass, connectable=True
            )
            if format_mac(discovery_info.address) not in configured
            and _is_supported(discovery_info)
        }


def _is_supported(discovery_info: BluetoothServiceInfoBleak) -> bool:
    """Report whether this advertisement belongs to a product we can talk to."""
    try:
        advertisement = parse_advertisement(
            discovery_info.service_data, discovery_info.manufacturer_data
        )
    except TuyaBleError:
        return False
    return product_for(advertisement.product_id) is not None


def _validate(user_input: TuyaBleCredentialsInput) -> dict[str, str]:
    """
    Reject credentials that cannot possibly work, before anything is stored.

    Only the shape is checked here; whether the device accepts them is decided
    on the first poll, when it is awake.
    """
    errors: dict[str, str] = {}
    if not user_input["device_id"].strip():
        errors[CONF_DEVICE_ID] = "invalid_device_id"
    if len(user_input["local_key"].strip()) < MIN_LOCAL_KEY_LENGTH:
        errors[CONF_LOCAL_KEY] = "invalid_local_key"
    return errors
