"""Sensor platform for tuya_ble."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.sensor import SensorEntity

from .entity import TuyaBleEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .data import TuyaBleConfigEntry, TuyaBlePost


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: TuyaBleConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    async_add_entities(
        [TuyaBleTitleSensor(coordinator=entry.runtime_data.coordinator)],
    )


class TuyaBleTitleSensor(TuyaBleEntity, SensorEntity):
    """Sensor exposing the latest post title returned by the API."""

    _attr_translation_key = "title"

    @property
    def unique_id(self) -> str:
        """Return a unique id derived from the config entry id."""
        return f"{self.coordinator.config_entry.entry_id}_title"

    @property
    def native_value(self) -> str | None:
        """
        Return the title from the latest fetched post, if any.

        ``coordinator.data`` is typed as the post payload because that's the
        coordinator's TypeVar binding, but at runtime it can still be ``None``
        before the first successful refresh.
        """
        data: TuyaBlePost | None = self.coordinator.data
        if data is None:
            return None
        return data["title"]
