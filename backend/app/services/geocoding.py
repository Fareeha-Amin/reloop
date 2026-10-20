"""Geocoding interface.

!!! STUB !!! No real geocoding happens in Phase 1. The only implementation,
PassthroughGeocoder, returns the coordinates the client supplied, unchanged and
unverified. It does not look up the address, check that the coordinates match it, or
call any maps API. No maps API key exists.

A real implementation (Google Maps / Mapbox, caching every result by normalised address)
replaces it by implementing `Geocoder` and changing `get_geocoder`. Nothing else changes.
"""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Location:
    address_text: str
    latitude: float
    longitude: float


class GeocodingUnavailable(Exception):
    pass


class Geocoder(Protocol):
    def resolve(
        self, address_text: str, latitude: float | None, longitude: float | None
    ) -> Location:
        """Return coordinates for an address. A real geocoder may ignore or verify the
        supplied coordinates; it must not silently invent them."""
        ...


class PassthroughGeocoder:
    """STUB. Returns the supplied coordinates as-is. See module docstring."""

    is_stub = True

    def resolve(
        self, address_text: str, latitude: float | None, longitude: float | None
    ) -> Location:
        if latitude is None or longitude is None:
            raise GeocodingUnavailable(
                "No geocoder is configured (stub). Supply latitude and longitude."
            )
        return Location(address_text=address_text, latitude=latitude, longitude=longitude)


def get_geocoder() -> Geocoder:
    return PassthroughGeocoder()
