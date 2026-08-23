"""Typed shape of the Tuya account the setup form can ask for."""

from __future__ import annotations

from typing import TypedDict


class TuyaBleAccountCredentials(TypedDict):
    """
    What the optional account form collects.

    These credentials open the Tuya account long enough to read one device's
    own credentials from it, and are never written to the config entry: the
    integration talks to the device over Bluetooth and needs no account at
    runtime.
    """

    email: str
    password: str
    country_code: str
    region: str
