"""Config flow for tuya_ble."""

from __future__ import annotations

from typing import TYPE_CHECKING, NotRequired, TypedDict, cast

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components.bluetooth import async_discovered_service_info
from homeassistant.const import (
    CONF_ADDRESS,
    CONF_DEVICE_ID,
    CONF_EMAIL,
    CONF_PASSWORD,
    CONF_REGION,
)
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.device_registry import format_mac
from tuya_ble_sdk import (
    DEFAULT_REGION,
    REGIONS,
    TuyaBleAuthenticationError,
    TuyaBleCloudError,
    TuyaBleConnectionError,
    TuyaBleError,
    parse_advertisement,
)

from .account import TuyaBleAccount
from .const import (
    CONF_COUNTRY_CODE,
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
    from tuya_ble_sdk import CloudDevice

    from .data import (
        TuyaBleAccountCredentials,
        TuyaBleConfigData,
        TuyaBleConfigEntry,
    )
    from .products import TuyaBleProduct

_PAIRING_METHODS = ["account", "manual"]


class TuyaBleCredentialsInput(TypedDict):
    """What the manual form collects: the credentials, and sometimes the product."""

    device_id: str
    local_key: str
    product_id: NotRequired[str]


def _account_schema(defaults: TuyaBleAccountCredentials | None = None) -> vol.Schema:
    """Build the account form, keeping what the user already typed."""
    return vol.Schema(
        {
            vol.Required(
                CONF_EMAIL,
                default=defaults["email"] if defaults else vol.UNDEFINED,
            ): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.EMAIL),
            ),
            vol.Required(CONF_PASSWORD): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD),
            ),
            vol.Required(
                CONF_COUNTRY_CODE,
                default=defaults["country_code"] if defaults else vol.UNDEFINED,
            ): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT),
            ),
            vol.Required(
                CONF_REGION,
                default=defaults["region"] if defaults else DEFAULT_REGION,
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=list(REGIONS),
                    mode=selector.SelectSelectorMode.DROPDOWN,
                    translation_key="region",
                ),
            ),
        },
    )


def _credentials_schema(
    defaults: TuyaBleCredentialsInput | None = None,
    *,
    ask_for_product: bool = False,
) -> vol.Schema:
    """
    Build the manual schema, optionally pre-filled.

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

    The credentials reach the entry one of two ways: read from the Tuya
    account the device is bound to, or typed in. Either way they are not tried
    against the device while the flow is open — these sensors sleep between
    advertisements, so a connection attempt would time out far more often than
    it would catch a typo. A wrong local key surfaces on the first poll
    instead, as a reauth prompt.
    """

    VERSION = 1

    _address: str
    _product: TuyaBleProduct | None
    _uuid: str
    _name: str
    _entry: config_entries.ConfigEntry | None = None

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
        user_input: TuyaBleCredentialsInput | None = None,  # noqa: ARG002
    ) -> config_entries.ConfigFlowResult:
        """Ask where the credentials that pair this device should come from."""
        return self.async_show_menu(
            step_id="bluetooth_confirm",
            menu_options=_PAIRING_METHODS,
            description_placeholders={"name": self._name},
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

    async def async_step_account(
        self,
        user_input: TuyaBleAccountCredentials | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Read the credentials of this device off the Tuya account."""
        errors: dict[str, str] = {}

        if user_input is not None:
            device, errors = await self._async_lookup(user_input)
            if device is not None:
                product = self._product or product_for(device.product_id)
                if product is None:
                    errors = {"base": "unsupported_product"}
                else:
                    return self._async_store(
                        product, device.device_id, device.local_key
                    )

        return self.async_show_form(
            step_id="account",
            data_schema=_account_schema(user_input),
            description_placeholders={"name": self._name},
            errors=errors,
        )

    async def async_step_manual(
        self,
        user_input: TuyaBleCredentialsInput | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Take the credentials of this device as the user copied them."""
        errors: dict[str, str] = {}
        ask_for_product = self._product is None

        if user_input is not None:
            errors = _validate(user_input)
            if not errors:
                product = self._product or SUPPORTED_PRODUCTS[user_input["product_id"]]
                return self._async_store(
                    product,
                    user_input["device_id"].strip(),
                    user_input["local_key"].strip(),
                )

        return self.async_show_form(
            step_id="manual",
            data_schema=_credentials_schema(
                user_input or self._known_credentials(),
                ask_for_product=ask_for_product,
            ),
            description_placeholders={"name": self._name},
            errors=errors,
        )

    async def async_step_reauth(
        self,
        entry_data: Mapping[str, str],  # noqa: ARG002
    ) -> config_entries.ConfigFlowResult:
        """Trigger reauth when the device rejects the stored local key."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self,
        user_input: TuyaBleCredentialsInput | None = None,  # noqa: ARG002
    ) -> config_entries.ConfigFlowResult:
        """Ask where the fresh credentials should come from."""
        self._adopt_entry(self._get_reauth_entry())
        return self.async_show_menu(
            step_id="reauth_confirm",
            menu_options=_PAIRING_METHODS,
            description_placeholders={"name": self._name},
        )

    async def async_step_reconfigure(
        self,
        user_input: TuyaBleCredentialsInput | None = None,  # noqa: ARG002
    ) -> config_entries.ConfigFlowResult:
        """Ask where the credentials of an existing entry should come from."""
        self._adopt_entry(self._get_reconfigure_entry())
        return self.async_show_menu(
            step_id="reconfigure",
            menu_options=_PAIRING_METHODS,
            description_placeholders={"name": self._name},
        )

    async def _async_lookup(
        self, credentials: TuyaBleAccountCredentials
    ) -> tuple[CloudDevice | None, dict[str, str]]:
        """Ask the account about this device, translating what can go wrong."""
        account = TuyaBleAccount(self.hass, credentials)
        try:
            device = await account.async_device_at(self._uuid, self._address)
        except TuyaBleAuthenticationError as exception:
            LOGGER.warning("The Tuya account rejected the credentials: %s", exception)
            return None, {"base": "invalid_auth"}
        except TuyaBleConnectionError as exception:
            LOGGER.error("Failed to reach the Tuya account: %s", exception)
            return None, {"base": "cannot_connect"}
        except TuyaBleCloudError as exception:
            LOGGER.warning("The Tuya account refused the lookup: %s", exception)
            return None, {"base": "account_busy"}
        except TuyaBleError:
            LOGGER.exception("Failed to read the Tuya account")
            return None, {"base": "unknown"}
        if device is None:
            return None, {"base": "device_not_in_account"}
        return device, {}

    def _async_store(
        self, product: TuyaBleProduct, device_id: str, local_key: str
    ) -> config_entries.ConfigFlowResult:
        """
        Create the entry, or update the one this flow was started for.

        An existing entry is left to the update listener to reload.
        ``async_update_reload_and_abort`` would schedule a second reload on top
        of the listener's, which Home Assistant reports as misuse and stops
        supporting in 2026.12.
        """
        if self._entry is not None:
            self.hass.config_entries.async_update_entry(
                self._entry,
                data={
                    **self._entry.data,
                    CONF_DEVICE_ID: device_id,
                    CONF_LOCAL_KEY: local_key,
                },
            )
            return self.async_abort(
                reason="reauth_successful"
                if self.source == config_entries.SOURCE_REAUTH
                else "reconfigure_successful"
            )

        return self.async_create_entry(
            title=_entry_title(product, self._address),
            data=cast(
                "TuyaBleConfigData",
                {
                    CONF_ADDRESS: self._address,
                    CONF_PRODUCT_ID: product.product_id,
                    CONF_UUID: self._uuid,
                    CONF_DEVICE_ID: device_id,
                    CONF_LOCAL_KEY: local_key,
                },
            ),
        )

    def _known_credentials(self) -> TuyaBleCredentialsInput | None:
        """Pre-fill the manual form with the device id an entry already has."""
        if self._entry is None:
            return None
        existing = cast("TuyaBleConfigData", self._entry.data)
        return TuyaBleCredentialsInput(device_id=existing["device_id"], local_key="")

    def _adopt(self, discovery_info: BluetoothServiceInfoBleak) -> bool:
        """
        Read the advertisement and keep what it discloses.

        Only the uuid is mandatory — it is what the pairing handshake needs and
        what ties the device to its record on the Tuya account. The product is
        optional: a bound device does not broadcast a readable product id, and
        it is read from the account or asked for instead.
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

    def _adopt_entry(self, entry: config_entries.ConfigEntry) -> None:
        """Describe the device from the entry being re-authenticated or edited."""
        existing = cast("TuyaBleConfigData", entry.data)
        self._entry = entry
        self._address = existing["address"]
        self._product = product_for(existing["product_id"])
        self._uuid = existing["uuid"]
        self._name = entry.title

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
