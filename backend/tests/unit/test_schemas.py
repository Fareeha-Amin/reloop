from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from app.constants import QUANTITY_MAX
from app.schemas.donation import DonationCreate, DonationUpdate, validate_pickup_window
from app.schemas.need import NeedUpdate
from app.schemas.organization import AcceptorRegister, OrganizationCreate, OrganizationUpdate
from tests.api.helpers import donation_payload, organization_payload

NOW = datetime(2026, 10, 20, 12, 0, tzinfo=UTC)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("pickup_latitude", 90.0001),
        ("pickup_latitude", -90.0001),
        ("pickup_longitude", 180.0001),
        ("pickup_longitude", -180.0001),
    ],
)
def test_donation_coordinates_out_of_range(field, value):
    with pytest.raises(ValidationError):
        DonationCreate(**donation_payload(**{field: value}))


@pytest.mark.parametrize("lat", [90, -90])
def test_donation_coordinate_bounds_are_inclusive(lat):
    DonationCreate(**donation_payload(pickup_latitude=lat))


@pytest.mark.parametrize("quantity", [0, -1, QUANTITY_MAX + 1])
def test_quantity_is_a_positive_bounded_item_count(quantity):
    with pytest.raises(ValidationError):
        DonationCreate(**donation_payload(quantity=quantity))


@pytest.mark.parametrize(
    ("field", "value"), [("category", "FOOD"), ("condition", "BROKEN"), ("category", "clothes")]
)
def test_unknown_vocabulary_values_rejected(field, value):
    with pytest.raises(ValidationError):
        DonationCreate(**donation_payload(**{field: value}))


def test_status_cannot_be_set_through_create_or_update():
    with pytest.raises(ValidationError):
        DonationCreate(**donation_payload(status="CANCELLED"))
    with pytest.raises(ValidationError):
        DonationUpdate(status="CANCELLED")


def test_pickup_window_order_and_future():
    validate_pickup_window(NOW + timedelta(hours=1), NOW + timedelta(hours=2), now=NOW)
    with pytest.raises(ValueError, match="after"):
        validate_pickup_window(NOW + timedelta(hours=2), NOW + timedelta(hours=1), now=NOW)
    with pytest.raises(ValueError, match="future"):
        validate_pickup_window(NOW - timedelta(hours=2), NOW - timedelta(hours=1), now=NOW)


def test_naive_datetimes_rejected():
    with pytest.raises(ValidationError):
        DonationCreate(**donation_payload(pickup_window_start="2030-01-01T10:00:00"))


def test_update_coordinates_must_come_in_pairs():
    with pytest.raises(ValidationError, match="together"):
        DonationUpdate(pickup_latitude=12.9)


def test_update_address_requires_new_coordinates():
    with pytest.raises(ValidationError, match="requires new latitude"):
        DonationUpdate(pickup_address_text="New address")
    DonationUpdate(pickup_address_text="New address", pickup_latitude=12.9, pickup_longitude=77.6)


def test_update_explicit_null_only_for_clearable_fields():
    assert DonationUpdate(note=None).note is None
    with pytest.raises(ValidationError, match="cannot be null"):
        DonationUpdate(quantity=None)
    with pytest.raises(ValidationError, match="cannot be null"):
        NeedUpdate(is_active=None)


def test_organisation_needs_at_least_one_distinct_category():
    with pytest.raises(ValidationError):
        OrganizationCreate(**organization_payload(categories_accepted=[]))
    with pytest.raises(ValidationError, match="duplicates"):
        OrganizationCreate(**organization_payload(categories_accepted=["BOOKS", "BOOKS"]))


def test_organisation_identity_fields_cannot_be_updated():
    with pytest.raises(ValidationError):
        OrganizationUpdate(name="A different organisation")
    with pytest.raises(ValidationError):
        OrganizationUpdate(registration_id="NEW-ID")
    with pytest.raises(ValidationError):
        OrganizationUpdate(verification_status="VERIFIED")


@pytest.mark.parametrize("schema", [AcceptorRegister, DonationCreate])
def test_docs_examples_are_valid_requests(schema):
    """The examples pre-filled in /docs must be accepted as-is, and the schemas must
    still reject unknown fields after adding them."""
    for example in schema.model_config["json_schema_extra"]["examples"]:
        schema.model_validate(example)
    assert schema.model_config["extra"] == "forbid"


def test_storage_capacity_cannot_be_negative():
    with pytest.raises(ValidationError):
        OrganizationCreate(**organization_payload(storage_capacity=-1))
