"""Migrations: `alembic upgrade head` works on an empty database, downgrades cleanly, and
leaves a schema identical to the models."""

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import inspect

import app.models  # noqa: F401
from app.db import Base
from tests.conftest import alembic_config, drop_everything, upgrade_head

from alembic import command

PHASE1_TABLES = {"users", "organization_profiles", "current_needs", "donations", "donation_images"}
PHASE2_TABLES = {
    "ranking_runs",
    "matches",
    "handovers",
    "status_events",
    "address_access_events",
    "waste_collectors",
    "recyclings",
}
PHASE3_TABLES = {"chat_messages", "chat_reads"}
PHASE4_TABLES = {"logistics_providers", "bookings", "payments", "commissions", "wallet_txns"}
PHASE5_TABLES = {"impact_records"}
APP_TABLES = PHASE1_TABLES | PHASE2_TABLES | PHASE3_TABLES | PHASE4_TABLES | PHASE5_TABLES


def _tables(engine) -> set[str]:
    return set(inspect(engine).get_table_names())


def test_upgrade_head_on_an_empty_database(test_engine):
    drop_everything(test_engine)
    assert _tables(test_engine) == set()

    upgrade_head(test_engine)
    assert _tables(test_engine) == APP_TABLES | {"alembic_version"}


def test_downgrade_to_base_and_back(test_engine):
    with test_engine.begin() as conn:
        command.downgrade(alembic_config(conn), "base")
    assert _tables(test_engine) - {"alembic_version"} == set()
    upgrade_head(test_engine)
    assert APP_TABLES <= _tables(test_engine)


def test_models_match_migrations(test_engine):
    with test_engine.connect() as conn:
        ctx = MigrationContext.configure(conn, opts={"compare_type": True})
        diff = compare_metadata(ctx, Base.metadata)
    assert diff == [], f"Models and migrations differ; create a migration:\n{diff}"


def test_downgrade_one_step_leaves_phase1_intact(test_engine):
    with test_engine.begin() as conn:
        command.downgrade(alembic_config(conn), "0001")
    assert _tables(test_engine) - {"alembic_version"} == PHASE1_TABLES
    upgrade_head(test_engine)
    assert APP_TABLES <= _tables(test_engine)


def test_only_expected_tables_exist():
    """Tables arrive with the code that uses them: no Review yet."""
    assert set(Base.metadata.tables) == APP_TABLES


# --- 0006: impact records and the donation without a condition -----------------------------


def _reset(engine):
    drop_everything(engine)
    upgrade_head(engine)


def test_0006_backfills_one_impact_record_per_finished_donation(test_engine):
    """Donations finished before 0006 get their impact record: reuse counts carbon and
    names the accepting organisation; recycling counts mass only; a listed donation none."""
    from datetime import UTC, datetime, timedelta
    from decimal import Decimal

    from sqlalchemy import select
    from sqlalchemy.orm import Session

    from app.constants import (
        CATEGORY_WEIGHT_KG,
        CARBON_FACTOR_KG_PER_ITEM,
        Category,
        Condition,
        DonationStatus,
        ImpactOutcome,
        OfferResponse,
        OfferSource,
        RankingTrigger,
        Role,
        VerificationStatus,
    )
    from app.models import Donation, ImpactRecord, Match, OrganizationProfile, RankingRun, User

    drop_everything(test_engine)
    upgrade_head(test_engine)
    with test_engine.begin() as conn:
        command.downgrade(alembic_config(conn), "0005")

    try:
        now = datetime.now(UTC)
        with Session(test_engine) as s:
            donor = User(email="donor@example.org", password_hash="x", role=Role.DONOR, full_name="Donor")
            org_user = User(email="org@example.org", password_hash="x", role=Role.ACCEPTOR, full_name="Org")
            s.add_all([donor, org_user])
            s.flush()
            org = OrganizationProfile(
                user_id=org_user.id, name="Org", registration_id="MIG-1", contact_person="C",
                phone="+911234567", address_text="A", latitude=12.97, longitude=77.59,
                pickup_capable=False, storage_capacity=100, categories_accepted=[Category.TOYS],
                verification_status=VerificationStatus.VERIFIED,
            )
            s.add(org)
            s.flush()

            def donation(status, quantity):
                return Donation(
                    donor_id=donor.id, category=Category.TOYS, quantity=quantity,
                    condition=Condition.USED, pickup_address_text="A", pickup_latitude=12.97,
                    pickup_longitude=77.59, pickup_window_start=now + timedelta(days=1),
                    pickup_window_end=now + timedelta(days=2), status=status,
                )

            reused = donation(DonationStatus.COMPLETED, 4)
            recycled = donation(DonationStatus.RECYCLED, 3)
            listed = donation(DonationStatus.LISTED, 2)
            s.add_all([reused, recycled, listed])
            s.flush()
            run = RankingRun(
                donation_id=reused.id, trigger=RankingTrigger.DONOR_OFFER, radius_km=15.0, declines=0,
                config_version="mig", config={}, slate=[], filtered_out={},
            )
            s.add(run)
            s.flush()
            s.add(
                Match(
                    donation_id=reused.id, organization_id=org.id, ranking_run_id=run.id, rank=1,
                    offered_by=OfferSource.DONOR, offered_at=now, expires_at=now + timedelta(days=2),
                    response=OfferResponse.ACCEPTED, responded_at=now,
                )
            )
            s.commit()
            reused_id, recycled_id, listed_id, org_id = reused.id, recycled.id, listed.id, org.id

        upgrade_head(test_engine)

        with Session(test_engine) as s:
            rows = {r.donation_id: r for r in s.scalars(select(ImpactRecord))}
        assert set(rows) == {reused_id, recycled_id}
        assert listed_id not in rows

        r = rows[reused_id]
        assert r.outcome == ImpactOutcome.REUSED and r.organization_id == org_id
        assert r.mass_kg == CATEGORY_WEIGHT_KG[Category.TOYS] * 4
        assert r.carbon_kg == CARBON_FACTOR_KG_PER_ITEM[Category.TOYS] * 4

        k = rows[recycled_id]
        assert k.outcome == ImpactOutcome.RECYCLED and k.organization_id is None
        assert k.mass_kg == CATEGORY_WEIGHT_KG[Category.TOYS] * 3
        assert k.carbon_kg is None and k.carbon_kg_per_item is None
    finally:
        _reset(test_engine)


def test_downgrade_refuses_while_a_donation_has_no_condition(test_engine):
    """A donation sent to recycling has no condition, which 0005's column cannot hold.
    The downgrade refuses rather than invent a value or delete the donation."""
    from datetime import UTC, datetime, timedelta

    from sqlalchemy.orm import Session

    from app.constants import Category, DonationStatus, Role
    from app.models import Donation, User

    _reset(test_engine)
    now = datetime.now(UTC)
    with Session(test_engine) as s:
        donor = User(email="nocond@example.org", password_hash="x", role=Role.DONOR, full_name="Donor")
        s.add(donor)
        s.flush()
        s.add(
            Donation(
                donor_id=donor.id, category=Category.BOOKS, quantity=1, condition=None,
                pickup_address_text="A", pickup_latitude=12.97, pickup_longitude=77.59,
                pickup_window_start=now + timedelta(days=1), pickup_window_end=now + timedelta(days=2),
                status=DonationStatus.WASTE_REDIRECTED,
            )
        )
        s.commit()
    try:
        with pytest.raises(RuntimeError, match="without a condition"):
            with test_engine.begin() as conn:
                command.downgrade(alembic_config(conn), "0005")
    finally:
        _reset(test_engine)


# --- 0007: the recycling handover step -----------------------------------------------------


def _donor_and_recycling(engine):
    """A donor, a waste collector and an open Recycling assignment, for the tests below."""
    from datetime import UTC, datetime, timedelta
    from decimal import Decimal

    from sqlalchemy.orm import Session

    from app.constants import Category, DonationStatus, Role
    from app.models import Donation, Recycling, User, WasteCollector

    now = datetime.now(UTC)
    with Session(engine) as s:
        donor = User(email="recycler-mig@example.org", password_hash="x", role=Role.DONOR, full_name="Donor")
        s.add(donor)
        s.flush()
        collector = WasteCollector(
            name="Mig Recycler", address_text="A", latitude=12.97, longitude=77.59,
            categories_accepted=[Category.BOOKS], rate_per_kg=Decimal("5.00"),
        )
        s.add(collector)
        s.flush()
        donation = Donation(
            donor_id=donor.id, category=Category.BOOKS, quantity=1, condition=None,
            pickup_address_text="A", pickup_latitude=12.97, pickup_longitude=77.59,
            pickup_window_start=now + timedelta(days=1), pickup_window_end=now + timedelta(days=2),
            status=DonationStatus.WASTE_REDIRECTED,
        )
        s.add(donation)
        s.flush()
        recycling = Recycling(
            donation_id=donation.id, collector_id=collector.id, distance_km=1.0,
            rate_per_kg=collector.rate_per_kg, assigned_by_id=donor.id,
        )
        s.add(recycling)
        s.commit()
        return donor.id, donation.id, recycling.id


def test_handovers_require_exactly_one_of_match_or_recycling(test_engine):
    """The CHECK constraint added in 0007, not just app code: a row with both set, or
    neither, is rejected by the database itself."""
    from datetime import UTC, datetime, timedelta

    from sqlalchemy.exc import IntegrityError
    from sqlalchemy.orm import Session

    from app.constants import HandoverMode
    from app.models import Handover

    donor_id, _, _ = _donor_and_recycling(test_engine)
    try:
        now = datetime.now(UTC)
        with Session(test_engine) as s:
            s.add(
                Handover(
                    recycling_id=None, mode=HandoverMode.DONOR_DROPOFF,
                    scheduled_for=now + timedelta(days=1), arranged_by_id=donor_id,
                )
            )
            with pytest.raises(IntegrityError, match="handover_exactly_one_of_match_or_recycling"):
                s.commit()
    finally:
        _reset(test_engine)


def test_downgrade_refuses_while_a_handover_is_recorded_against_a_recycling(test_engine):
    """A handover against a recycling has no match_id the old schema can hold. The
    downgrade refuses rather than invent one or delete the record."""
    from datetime import UTC, datetime, timedelta

    from sqlalchemy.orm import Session

    from app.constants import HandoverMode
    from app.models import Handover

    donor_id, _, recycling_id = _donor_and_recycling(test_engine)
    now = datetime.now(UTC)
    with Session(test_engine) as s:
        s.add(
            Handover(
                recycling_id=recycling_id, mode=HandoverMode.DONOR_DROPOFF,
                scheduled_for=now, arranged_by_id=donor_id,
            )
        )
        s.commit()
    try:
        with pytest.raises(RuntimeError, match="cannot represent"):
            with test_engine.begin() as conn:
                command.downgrade(alembic_config(conn), "0006")
    finally:
        _reset(test_engine)
