import uuid
from datetime import datetime
from typing import Annotated

from pydantic import (
    ConfigDict,
    EmailStr,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.constants import (
    REGISTRATION_ID_MAX_LENGTH,
    STORAGE_CAPACITY_MAX,
    Category,
    VerificationStatus,
)
from app.schemas.common import (
    Address,
    InputModel,
    Latitude,
    Longitude,
    Name,
    Note,
    OutputModel,
    Phone,
    check_location_update,
    reject_explicit_nulls,
)
from app.schemas.need import NeedOut
from app.schemas.user import Password, UserOut

RegistrationId = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=REGISTRATION_ID_MAX_LENGTH),
]
StorageCapacity = Annotated[
    int, Field(ge=0, le=STORAGE_CAPACITY_MAX, description="A count of items.")
]


def _distinct_categories(value: list[Category]) -> list[Category]:
    if len(set(value)) != len(value):
        raise ValueError("categories_accepted contains duplicates.")
    return value


class OrganizationCreate(InputModel):
    name: Name
    registration_id: RegistrationId
    contact_person: Name
    phone: Phone
    address_text: Address
    latitude: Latitude
    longitude: Longitude
    pickup_capable: bool
    storage_capacity: StorageCapacity
    categories_accepted: list[Category] = Field(min_length=1)

    @field_validator("categories_accepted")
    @classmethod
    def distinct_categories(cls, value: list[Category]) -> list[Category]:
        return _distinct_categories(value)


class AcceptorRegister(InputModel):
    """Creates the acceptor's login and its organisation profile together.
    The organisation starts PENDING; only an admin can verify it."""

    # Shown pre-filled in /docs. Login fields at the top level, organisation nested.
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "email": "sunrise@example.org",
                    "password": "sunrise-home-2026",
                    "full_name": "Meera Iyer",
                    "phone": "+91 98450 11111",
                    "organization": {
                        "name": "Sunrise Home",
                        "registration_id": "KA-1",
                        "contact_person": "Meera Iyer",
                        "phone": "+91 80 2222 3333",
                        "address_text": "12 MG Road, Bengaluru",
                        "latitude": 12.9716,
                        "longitude": 77.5946,
                        "pickup_capable": True,
                        "storage_capacity": 200,
                        "categories_accepted": [Category.CLOTHES.value, Category.BOOKS.value],
                    },
                }
            ]
        }
    )

    email: EmailStr
    password: Password
    full_name: Name
    phone: Phone
    organization: OrganizationCreate


class OrganizationUpdate(InputModel):
    """Operational fields only. name and registration_id cannot change after
    registration (unknown fields are rejected), so a verified organisation cannot
    become a different one."""

    contact_person: Name | None = None
    phone: Phone | None = None
    address_text: Address | None = None
    latitude: Latitude | None = None
    longitude: Longitude | None = None
    pickup_capable: bool | None = None
    storage_capacity: StorageCapacity | None = None
    categories_accepted: list[Category] | None = Field(default=None, min_length=1)

    @field_validator("categories_accepted")
    @classmethod
    def distinct_categories(cls, value: list[Category] | None) -> list[Category] | None:
        return value if value is None else _distinct_categories(value)

    @model_validator(mode="after")
    def check_partial_update(self):
        reject_explicit_nulls(self)
        check_location_update(self.address_text, self.latitude, self.longitude)
        return self


class OrganizationOut(OutputModel):
    id: uuid.UUID
    name: str
    registration_id: str
    contact_person: str
    phone: str
    address_text: str
    latitude: float
    longitude: float
    pickup_capable: bool
    storage_capacity: int = Field(description="A count of items.")
    categories_accepted: list[Category]
    verification_status: VerificationStatus
    verification_note: str | None
    verification_updated_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AcceptorRegistered(OutputModel):
    user: UserOut
    organization: OrganizationOut


class AdminOrganizationDetail(OrganizationOut):
    account_email: str
    needs: list[NeedOut]


class OrganizationCountsOut(OutputModel):
    by_status: dict[VerificationStatus, int] = Field(description="Every verification status, zero included.")
    awaiting_verification: int = Field(description="Organisations an admin has yet to verify or reject.")


class VerificationUpdate(InputModel):
    status: VerificationStatus
    note: Note | None = None
