"""Phase 1 foundation: users, organisations, needs, donations, donation images.

Vocabulary columns (role, category, condition, urgency, status, verification_status)
are plain VARCHAR(32): values are validated in code against app.constants, with no
native ENUM types and no CHECK constraints repeating them. The default values written
here ('PENDING', 'LISTED') are a frozen snapshot, as migrations must be.

Revision ID: 0001
Revises:
Create Date: 2026-10-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("full_name", sa.String(length=200), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=True),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )

    op.create_table(
        "organization_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("registration_id", sa.String(length=64), nullable=False),
        sa.Column("contact_person", sa.String(length=200), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=False),
        sa.Column("address_text", sa.String(length=300), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("pickup_capable", sa.Boolean(), nullable=False),
        sa.Column("storage_capacity", sa.Integer(), nullable=False),
        sa.Column("categories_accepted", postgresql.ARRAY(sa.String(length=32)), nullable=False),
        sa.Column("verification_status", sa.String(length=32), server_default="PENDING", nullable=False),
        sa.Column("verification_note", sa.Text(), nullable=True),
        sa.Column("verification_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verification_updated_by_id", sa.Uuid(), nullable=True),
        *_timestamps(),
        sa.CheckConstraint("storage_capacity >= 0", name="ck_organization_profiles_storage_capacity_non_negative"),
        sa.CheckConstraint("latitude BETWEEN -90 AND 90", name="ck_organization_profiles_latitude_range"),
        sa.CheckConstraint("longitude BETWEEN -180 AND 180", name="ck_organization_profiles_longitude_range"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_organization_profiles_user_id_users"),
        sa.ForeignKeyConstraint(
            ["verification_updated_by_id"],
            ["users.id"],
            name="fk_organization_profiles_verification_updated_by_id_users",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_organization_profiles"),
        # One login per organisation.
        sa.UniqueConstraint("user_id", name="uq_organization_profiles_user_id"),
        sa.UniqueConstraint("registration_id", name="uq_organization_profiles_registration_id"),
    )

    op.create_table(
        "current_needs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("quantity_needed", sa.Integer(), nullable=False),
        sa.Column("urgency", sa.String(length=32), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        *_timestamps(),
        sa.CheckConstraint("quantity_needed >= 1", name="ck_current_needs_quantity_needed_positive"),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organization_profiles.id"],
            name="fk_current_needs_organization_id_organization_profiles",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_current_needs"),
    )
    op.create_index("ix_current_needs_organization_id", "current_needs", ["organization_id"])
    op.create_index(
        "uq_current_needs_one_active_per_category",
        "current_needs",
        ["organization_id", "category"],
        unique=True,
        postgresql_where=sa.text("is_active"),
    )

    op.create_table(
        "donations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("donor_id", sa.Uuid(), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("condition", sa.String(length=32), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("is_priority", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("pickup_address_text", sa.String(length=300), nullable=False),
        sa.Column("pickup_latitude", sa.Float(), nullable=False),
        sa.Column("pickup_longitude", sa.Float(), nullable=False),
        sa.Column("pickup_window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("pickup_window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="LISTED", nullable=False),
        *_timestamps(),
        sa.CheckConstraint("quantity >= 1", name="ck_donations_quantity_positive"),
        sa.CheckConstraint("pickup_latitude BETWEEN -90 AND 90", name="ck_donations_pickup_latitude_range"),
        sa.CheckConstraint("pickup_longitude BETWEEN -180 AND 180", name="ck_donations_pickup_longitude_range"),
        sa.CheckConstraint("pickup_window_end > pickup_window_start", name="ck_donations_pickup_window_order"),
        sa.ForeignKeyConstraint(["donor_id"], ["users.id"], name="fk_donations_donor_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_donations"),
    )
    op.create_index("ix_donations_donor_id", "donations", ["donor_id"])
    op.create_index("ix_donations_status", "donations", ["status"])

    op.create_table(
        "donation_images",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("donation_id", sa.Uuid(), nullable=False),
        sa.Column("storage_key", sa.String(length=128), nullable=False),
        sa.Column("content_type", sa.String(length=64), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["donation_id"], ["donations.id"], name="fk_donation_images_donation_id_donations"),
        sa.PrimaryKeyConstraint("id", name="pk_donation_images"),
        sa.UniqueConstraint("storage_key", name="uq_donation_images_storage_key"),
    )
    op.create_index("ix_donation_images_donation_id", "donation_images", ["donation_id"])


def downgrade() -> None:
    op.drop_table("donation_images")
    op.drop_table("donations")
    op.drop_table("current_needs")
    op.drop_table("organization_profiles")
    op.drop_table("users")
