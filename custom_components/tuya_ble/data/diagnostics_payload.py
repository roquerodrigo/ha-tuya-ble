"""Typed top-level shape returned by async_get_config_entry_diagnostics."""

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from .diagnostics_entry import TuyaBleDiagnosticsEntry
    from .post import TuyaBlePost


class TuyaBleDiagnosticsPayload(TypedDict):
    """Top-level shape returned by async_get_config_entry_diagnostics."""

    entry: TuyaBleDiagnosticsEntry
    coordinator_data: TuyaBlePost | None
