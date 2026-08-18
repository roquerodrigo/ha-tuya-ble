"""Constants for tuya_ble."""

from __future__ import annotations

from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

DOMAIN = "tuya_ble"
ATTRIBUTION = "Data provided by https://jsonplaceholder.typicode.com/"
API_BASE_URL = "https://jsonplaceholder.typicode.com"

DEFAULT_SCAN_INTERVAL_SECONDS = 300
MIN_SCAN_INTERVAL_SECONDS = 30
