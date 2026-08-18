"""Runtime data stored on entry.runtime_data."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.loader import Integration

    from ..coordinator import TuyaBleDataUpdateCoordinator
    from ..products import TuyaBleProduct


@dataclass
class TuyaBleData:
    """
    Data stored on entry.runtime_data for one Tuya BLE device.

    There is no long-lived client: a read owns its connection from end to end,
    so the coordinator builds one per poll and lets it go.
    """

    coordinator: TuyaBleDataUpdateCoordinator
    product: TuyaBleProduct
    integration: Integration
