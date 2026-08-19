"""The Tuya BLE products this integration knows how to talk to."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING

from .const import PRODUCT_ID_SOIL_SENSOR

if TYPE_CHECKING:
    from collections.abc import Mapping


@dataclass(frozen=True, slots=True)
class TuyaBleProduct:
    """
    A supported product, identified by what its advertisement discloses.

    The product id is the only identity a Tuya BLE device broadcasts, so it is
    what discovery matches on. The name is never shown: it is the translation
    key the device registry resolves, so the device is named in the user's own
    language.
    """

    product_id: str
    translation_key: str
    model: str


SUPPORTED_PRODUCTS: Mapping[str, TuyaBleProduct] = MappingProxyType(
    {
        PRODUCT_ID_SOIL_SENSOR: TuyaBleProduct(
            product_id=PRODUCT_ID_SOIL_SENSOR,
            translation_key="soil_sensor",
            model="SGS01",
        ),
    }
)


def product_for(product_id: str | None) -> TuyaBleProduct | None:
    """Return the product with this id, or ``None`` when it is not supported."""
    if product_id is None:
        return None
    return SUPPORTED_PRODUCTS.get(product_id)
