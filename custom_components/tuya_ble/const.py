"""Constants for tuya_ble."""

from __future__ import annotations

from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

DOMAIN = "tuya_ble"
MANUFACTURER = "Tuya"

CONF_LOCAL_KEY = "local_key"
CONF_PRODUCT_ID = "product_id"
CONF_UUID = "uuid"

DEFAULT_SCAN_INTERVAL_SECONDS = 900
MIN_SCAN_INTERVAL_SECONDS = 60

MIN_LOCAL_KEY_LENGTH = 6
