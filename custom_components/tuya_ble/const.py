"""Constants for tuya_ble."""

from __future__ import annotations

from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

DOMAIN = "tuya_ble"
MANUFACTURER = "Tuya"

PRODUCT_ID_SOIL_SENSOR = "gvygg3m8"

CONF_COUNTRY_CODE = "country_code"
CONF_LOCAL_KEY = "local_key"
CONF_PRODUCT_ID = "product_id"
CONF_UUID = "uuid"

DEFAULT_SCAN_INTERVAL_SECONDS = 900
MIN_SCAN_INTERVAL_SECONDS = 60

MIN_LOCAL_KEY_LENGTH = 6

SILENT_HANDSHAKES_BEFORE_REAUTH = 3

POLL_CHECK_INTERVAL_SECONDS = 30
