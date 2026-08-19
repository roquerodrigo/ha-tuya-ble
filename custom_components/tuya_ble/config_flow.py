"""Config flow for tuya_ble."""

from __future__ import annotations

from typing import TYPE_CHECKING, NotRequired, TypedDict, cast

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components.bluetooth import async_discovered_service_info
from homeassistant.const import CONF_ADDRESS, CONF_DEVICE_ID
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.device_registry import format_mac
from tuya_ble_sdk import TuyaBleError, parse_advertisement

from .const import (
    CONF_LOCAL_KEY,
    CONF_PRODUCT_ID,
    CONF_UUID,
    DOMAIN,
    LOGGER,
    MIN_LOCAL_KEY_LENGTH,
)
from .options_flow import TuyaBleOptionsFlow
from .products import SUPPORTED_PRODUCTS, product_for

if TYPE_CHECKING:
    from collections.abc import Mapping

    from homeassistant.components.bluetooth import BluetoothServiceInfoBleak

    from .data import TuyaBleConfigData, TuyaBleConfigEntry
    from .products import TuyaBleProduct


class TuyaBleCredentialsInput(TypedDict):
    """What the setup form collects: the credentials, and sometimes the product."""

    device_id: str
    local_key: str
    product_id: NotRequired[str]


def _credentials_schema(
    defaults: TuyaBleCredentialsInput | None = None,
    *,
    ask_for_product: bool = False,
) -> vol.Schema:
    """
    Build the setup schema, optionally pre-filled.

    The product is only asked for when the advertisement did not name it: a
    device that is bound to a Tuya account broadcasts an obfuscated value in
    place of its product id, so nothing in the air says what it is.
    """
    schema: dict[vol.Marker, selector.TextSelector | selector.SelectSelector] = {
        vol.Required(
            CONF_DEVICE_ID,
            default=defaults["device_id"] if defaults else vol.UNDEFINED,
        ): selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT),
        ),
        vol.Required(CONF_LOCAL_KEY): selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD),
        ),
    }
    if ask_for_product:
        schema[vol.Required(CONF_PRODUCT_ID)] = selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=sorted(SUPPORTED_PRODUCTS),
                translation_key="product",
            ),
        )
    return vol.Schema(schema)


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
    _product: TuyaBleProduct | None
    _uuid: str
    _name: str

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
        self.context["title_placeholders"] = {"name": self._name}
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
                product = self._product or SUPPORTED_PRODUCTS[user_input["product_id"]]
                return self.async_create_entry(
                    title=_entry_title(product, self._address),
                    data=cast(
                        "TuyaBleConfigData",
                        {
                            CONF_ADDRESS: self._address,
                            CONF_PRODUCT_ID: product.product_id,
                            CONF_UUID: self._uuid,
                            CONF_DEVICE_ID: user_input["device_id"].strip(),
                            CONF_LOCAL_KEY: user_input["local_key"].strip(),
                        },
                    ),
                )

        return self.async_show_form(
            step_id="bluetooth_confirm",
            data_schema=_credentials_schema(
                user_input, ask_for_product=self._product is None
            ),
            description_placeholders={"name": self._name},
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
        return await self._async_update_credentials(
            "reauth_confirm", "reauth_successful", user_input
        )

    async def async_step_reconfigure(
        self,
        user_input: TuyaBleCredentialsInput | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Allow editing the credentials of an existing entry."""
        return await self._async_update_credentials(
            "reconfigure", "reconfigure_successful", user_input
        )

    async def _async_update_credentials(
        self,
        step_id: str,
        abort_reason: str,
        user_input: TuyaBleCredentialsInput | None,
    ) -> config_entries.ConfigFlowResult:
        """
        Re-ask for the credentials of an entry that already exists.

        The entry is updated and left to the update listener to reload.
        ``async_update_reload_and_abort`` would schedule a second reload on top
        of the listener's, which Home Assistant reports as misuse and stops
        supporting in 2026.12.
        """
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
                self.hass.config_entries.async_update_entry(
                    entry,
                    data={
                        **entry.data,
                        CONF_DEVICE_ID: user_input["device_id"].strip(),
                        CONF_LOCAL_KEY: user_input["local_key"].strip(),
                    },
                )
                return self.async_abort(reason=abort_reason)

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
        """
        Read the advertisement and keep what it discloses.

        Only the uuid is mandatory — it is what the pairing handshake needs.
        The product is optional: a bound device does not broadcast a readable
        product id, and the user is asked for it instead.
        """
        try:
            advertisement = parse_advertisement(
                discovery_info.service_data, discovery_info.manufacturer_data
            )
        except TuyaBleError as exception:
            LOGGER.debug("Failed to read the advertisement: %s", exception)
            return False
        if advertisement.uuid is None:
            return False
        self._address = discovery_info.address
        self._product = product_for(advertisement.product_id)
        self._uuid = advertisement.uuid
        self._name = (
            _entry_title(self._product, self._address)
            if self._product
            else discovery_info.address
        )
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


def _entry_title(product: TuyaBleProduct, address: str) -> str:
    """
    Name the entry so two of the same product stay tellable apart.

    One entry is one physical device, and the model alone repeats across every
    unit of it, so the address — the only thing that differs — is part of the
    title.
    """
    return f"{product.model} {address.replace(':', '')[-6:]}"


def _is_supported(discovery_info: BluetoothServiceInfoBleak) -> bool:
    """Report whether this advertisement identifies a device we can pair with."""
    try:
        advertisement = parse_advertisement(
            discovery_info.service_data, discovery_info.manufacturer_data
        )
    except TuyaBleError:
        return False
    return advertisement.uuid is not None


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
