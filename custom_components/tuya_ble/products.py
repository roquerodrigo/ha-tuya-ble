"""The Tuya BLE products this integration knows how to talk to."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping


@dataclass(frozen=True, slots=True)
class TuyaBleProduct:
    """
    A supported product, identified by what its advertisement discloses.

    The product id is the only identity a Tuya BLE device broadcasts, so it is
    what discovery matches on; the model and the name are what the device
    registry shows.
    """

    product_id: str
    name: str
    model: str


SUPPORTED_PRODUCTS: Mapping[str, TuyaBleProduct] = MappingProxyType(
    {
        "gvygg3m8": TuyaBleProduct(
            product_id="gvygg3m8",
            name="Soil sensor",
            model="SGS01",
        ),
    }
)


def product_for(product_id: str | None) -> TuyaBleProduct | None:
    """Return the product with this id, or ``None`` when it is not supported."""
    if product_id is None:
        return None
    return SUPPORTED_PRODUCTS.get(product_id)
