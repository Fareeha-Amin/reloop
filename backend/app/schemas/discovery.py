"""The public discovery map: verified organisations near you, and what they need.

No address, phone, contact person or registration ID, and positions rounded to
DISCOVERY_COORD_DECIMALS. Matching uses the precise positions; this view is for browsing.
"""

import uuid
from typing import Literal

from pydantic import Field

from app.constants import Category, Urgency
from app.domain import geo
from app.schemas.common import OutputModel


class DiscoveryNeedOut(OutputModel):
    category: Category
    quantity_needed: int = Field(description="A count of items.")
    urgency: Urgency


class DiscoveryOrganisationOut(OutputModel):
    id: uuid.UUID
    name: str
    latitude: float = Field(description="Approximate: rounded (see position_error_km).")
    longitude: float = Field(description="Approximate: rounded (see position_error_km).")
    pickup_capable: bool
    categories_accepted: list[Category]
    needs: list[DiscoveryNeedOut] = Field(description="Active needs only.")

    @classmethod
    def from_org(cls, org) -> "DiscoveryOrganisationOut":
        lat, lng = geo.approximate_position(org.latitude, org.longitude)
        return cls(
            id=org.id,
            name=org.name,
            latitude=lat,
            longitude=lng,
            pickup_capable=org.pickup_capable,
            categories_accepted=org.categories_accepted,
            needs=[DiscoveryNeedOut.model_validate(n) for n in org.needs if n.is_active],
        )


class DiscoveryOut(OutputModel):
    organisations: list[DiscoveryOrganisationOut]
    positions_are_approximate: Literal[True] = True
    position_error_km: float = Field(
        description="The furthest a shown position can be from the organisation's real one."
    )
