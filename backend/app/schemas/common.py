from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.constants import (
    ADDRESS_MAX_LENGTH,
    NAME_MAX_LENGTH,
    NOTE_MAX_LENGTH,
    PHONE_PATTERN,
    QUANTITY_MAX,
)

Latitude = Annotated[float, Field(ge=-90, le=90)]
Longitude = Annotated[float, Field(ge=-180, le=180)]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=NAME_MAX_LENGTH)]
Address = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=ADDRESS_MAX_LENGTH)
]
Note = Annotated[str, StringConstraints(strip_whitespace=True, max_length=NOTE_MAX_LENGTH)]
Phone = Annotated[str, StringConstraints(strip_whitespace=True, pattern=PHONE_PATTERN)]
# Counts of items, never kilograms.
ItemCount = Annotated[int, Field(ge=1, le=QUANTITY_MAX, description="A count of items.")]


class InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class OutputModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


def check_location_update(
    address_text: str | None, latitude: float | None, longitude: float | None
) -> None:
    """Coordinates come as a pair. A new address needs new coordinates too: the geocoder
    is a stub (app.services.geocoding), so keeping the old pin would silently mismatch."""
    if (latitude is None) != (longitude is None):
        raise ValueError("latitude and longitude must be given together.")
    if address_text is not None and latitude is None:
        raise ValueError("Changing the address requires new latitude and longitude.")


def reject_explicit_nulls(model: BaseModel, clearable: frozenset[str] = frozenset()) -> None:
    """In a partial update, an omitted field means 'leave unchanged'. An explicit null is
    only allowed for fields that may be cleared."""
    for name in model.model_fields_set - clearable:
        if getattr(model, name) is None:
            raise ValueError(f"{name} cannot be null.")
