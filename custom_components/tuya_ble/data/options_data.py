"""Typed shape of the options writable by the options flow."""

from __future__ import annotations

from typing import NotRequired, TypedDict


class TuyaBleOptionsData(TypedDict, total=False):
    """
    Shape of the options writable by the options flow.

    ``scan_interval`` is a float: the number selector that writes it hands
    Home Assistant a float even when the user types a whole number.
    """

    scan_interval: NotRequired[float]
