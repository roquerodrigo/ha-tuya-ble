"""Typed top-level shape returned by async_get_config_entry_diagnostics."""

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from collections.abc import Mapping

    from .diagnostics_entry import TuyaBleDiagnosticsEntry


class TuyaBleDiagnosticsPayload(TypedDict):
    """Top-level shape returned by async_get_config_entry_diagnostics."""

    entry: TuyaBleDiagnosticsEntry
    advertisement: Mapping[str, str | int | bool | None] | None
    data_points: Mapping[str, str | int | float | bool | None]
