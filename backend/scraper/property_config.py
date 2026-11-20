"""Property configuration for Azzurro Review Intelligence.

Central configuration of the four Booking.com properties that this
application monitors.  Each property exposes the fields required by the
collection engine, the analytics services and the API layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class PropertyConfig:
    """Immutable configuration record for a single property."""

    property_code: str
    name: str
    booking_url: str
    enabled: bool = True

    @property
    def slug(self) -> str:
        """URL-friendly identifier (matches ``property_code``)."""
        return self.property_code


PROPERTIES: List[PropertyConfig] = [
    PropertyConfig(
        property_code="olympic",
        name="Olympic Hotel Paddington",
        booking_url="https://www.booking.com/hotel/au/olympic-paddington.html",
    ),
    PropertyConfig(
        property_code="potts_point",
        name="Potts Point",
        booking_url="https://www.booking.com/hotel/au/venus-potts-point-sydney.html",
    ),
    PropertyConfig(
        property_code="central_sydney",
        name="Central Sydney",
        booking_url="https://www.booking.com/hotel/au/venus-surry-hills.html",
    ),
    PropertyConfig(
        property_code="darling_harbour",
        name="Darling Harbour",
        booking_url="https://www.booking.com/hotel/au/chateau-de-venus.html",
    ),
]


PROPERTY_MAP = {p.property_code: p for p in PROPERTIES}


def get_property(property_code: str) -> PropertyConfig | None:
    """Return the property configuration for ``property_code`` or ``None``."""
    return PROPERTY_MAP.get(property_code)


def get_all_properties() -> List[PropertyConfig]:
    """Return all configured properties."""
    return list(PROPERTIES)


def get_enabled_properties() -> List[PropertyConfig]:
    """Return only properties that are enabled for collection."""
    return [p for p in PROPERTIES if p.enabled]