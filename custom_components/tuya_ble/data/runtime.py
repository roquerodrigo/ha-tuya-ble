"""Runtime data stored on entry.runtime_data."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.loader import Integration

    from ..api import TuyaBleApiClient
    from ..coordinator import TuyaBleDataUpdateCoordinator


@dataclass
class TuyaBleData:
    """Data stored on entry.runtime_data for the Tuya BLE."""

    client: TuyaBleApiClient
    coordinator: TuyaBleDataUpdateCoordinator
    integration: Integration
