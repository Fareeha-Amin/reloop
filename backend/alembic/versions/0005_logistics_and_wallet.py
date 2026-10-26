"""Phase 4: logistics providers, platform-pickup bookings and their simulated payments,
the commission ledger, and the donor wallet ledger.

No existing table changes: HandoverMode gains PLATFORM_PICKUP and DonationAction gains
BOOK_PICKUP, both vocabulary values validated in code (app.constants), not schema
changes. Append-only and write-once rules are enforced in application code
(app.db.AppendOnly), not by triggers.

Data backfill: every Recycling already confirmed before this migration gets its wallet
credit and commission ledger rows now, so wallets and the commission ledger are correct
retroactively (CLAUDE.md: "Phase 4 wallets credit from confirmed rows ... including
those confirmed before this phase").

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | Sequence[str] | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "logistics_providers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("base_fee", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("per_km_rate", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        *_timestamps(),
        sa.CheckConstraint("base_fee >= 0", name="ck_logistics_providers_base_fee_non_negative"),
        sa.CheckConstraint("per_km_rate >= 0", name="ck_logistics_providers_per_km_rate_non_negative"),
        sa.PrimaryKeyConstraint("id", name="pk_logistics_providers"),
        sa.UniqueConstraint("name", name="uq_logistics_providers_name"),
    )

    op.create_table(
        "bookings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("donation_id", sa.Uuid(), nullable=False),
        sa.Column("handover_id", sa.Uuid(), nullable=False),
        sa.Column("provider_id", sa.Uuid(), nullable=False),
        sa.Column("distance_km", sa.Float(), nullable=False),
        sa.Column("cost", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("wallet_applied", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("gateway_amount", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("arranged_by_id", sa.Uuid(), nullable=False),
        sa.Column("booked_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("picked_up_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_reason", sa.Text(), nullable=True),
        sa.CheckConstraint("cost = wallet_applied + gateway_amount", name="ck_bookings_cost_splits_exactly"),
        sa.CheckConstraint(
            "NOT (delivered_at IS NOT NULL AND cancelled_at IS NOT NULL)",
            name="ck_bookings_not_both_delivered_and_cancelled",
        ),
        sa.CheckConstraint(
            "(cancelled_at IS NULL) = (cancel_reason IS NULL)", name="ck_bookings_cancel_reason_with_cancellation"
        ),
        sa.CheckConstraint("distance_km >= 0", name="ck_bookings_distance_non_negative"),
        sa.CheckConstraint(
            "cost >= 0 AND wallet_applied >= 0 AND gateway_amount >= 0", name="ck_bookings_amounts_non_negative"
        ),
        sa.ForeignKeyConstraint(["donation_id"], ["donations.id"], name="fk_bookings_donation_id_donations"),
        sa.ForeignKeyConstraint(["handover_id"], ["handovers.id"], name="fk_bookings_handover_id_handovers"),
        sa.ForeignKeyConstraint(
            ["provider_id"], ["logistics_providers.id"], name="fk_bookings_provider_id_logistics_providers"
        ),
        sa.ForeignKeyConstraint(["arranged_by_id"], ["users.id"], name="fk_bookings_arranged_by_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_bookings"),
        sa.UniqueConstraint("handover_id", name="uq_bookings_handover_id"),
    )
    op.create_index("ix_bookings_donation_id", "bookings", ["donation_id"])

    op.create_table(
        "payments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("booking_id", sa.Uuid(), nullable=False),
        sa.Column("donor_id", sa.Uuid(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("transaction_id", sa.String(length=64), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("refunded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("refund_transaction_id", sa.String(length=64), nullable=True),
        sa.CheckConstraint("amount >= 0", name="ck_payments_amount_non_negative"),
        sa.CheckConstraint(
            "(refunded_at IS NULL) = (refund_transaction_id IS NULL)", name="ck_payments_refund_has_transaction_id"
        ),
        sa.ForeignKeyConstraint(["booking_id"], ["bookings.id"], name="fk_payments_booking_id_bookings"),
        sa.ForeignKeyConstraint(["donor_id"], ["users.id"], name="fk_payments_donor_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_payments"),
        sa.UniqueConstraint("booking_id", name="uq_payments_booking_id"),
        sa.UniqueConstraint("transaction_id", name="uq_payments_transaction_id"),
        sa.UniqueConstraint("refund_transaction_id", name="uq_payments_refund_transaction_id"),
    )

    op.create_table(
        "commissions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_commissions"),
    )
    op.create_index("ix_commissions_source_id", "commissions", ["source_id"])

    op.create_table(
        "wallet_txns",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("donor_id", sa.Uuid(), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("reference_recycling_id", sa.Uuid(), nullable=True),
        sa.Column("reference_booking_id", sa.Uuid(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "(reference_recycling_id IS NOT NULL) != (reference_booking_id IS NOT NULL)",
            name="ck_wallet_txns_exactly_one_reference",
        ),
        sa.ForeignKeyConstraint(["donor_id"], ["users.id"], name="fk_wallet_txns_donor_id_users"),
        sa.ForeignKeyConstraint(
            ["reference_recycling_id"], ["recyclings.id"], name="fk_wallet_txns_reference_recycling_id_recyclings"
        ),
        sa.ForeignKeyConstraint(
            ["reference_booking_id"], ["bookings.id"], name="fk_wallet_txns_reference_booking_id_bookings"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_wallet_txns"),
    )
    op.create_index("ix_wallet_txns_donor_id", "wallet_txns", ["donor_id"])

    # --- Backfill: wallet credit and commission for every recycling confirmed before
    # this migration, so both ledgers are correct retroactively. ---------------------
    conn = op.get_bind()
    confirmed = conn.execute(
        sa.text(
            """
            SELECT r.id, d.donor_id, r.donor_credit, r.platform_fee, r.confirmed_at
            FROM recyclings r JOIN donations d ON d.id = r.donation_id
            WHERE r.confirmed_at IS NOT NULL
            """
        )
    ).fetchall()
    for recycling_id, donor_id, donor_credit, platform_fee, confirmed_at in confirmed:
        conn.execute(
            sa.text(
                """
                INSERT INTO wallet_txns (id, donor_id, type, amount, reference_recycling_id, note, created_at)
                VALUES (gen_random_uuid(), :donor_id, 'RECYCLING_CREDIT', :amount, :recycling_id,
                        'Recycling settlement (backfilled).', :at)
                """
            ),
            {"donor_id": donor_id, "amount": donor_credit, "recycling_id": recycling_id, "at": confirmed_at},
        )
        conn.execute(
            sa.text(
                """
                INSERT INTO commissions (id, source, source_id, amount, note, created_at)
                VALUES (gen_random_uuid(), 'RECYCLING', :recycling_id, :amount,
                        'Recycling settlement (backfilled).', :at)
                """
            ),
            {"recycling_id": recycling_id, "amount": platform_fee, "at": confirmed_at},
        )


def downgrade() -> None:
    op.drop_table("wallet_txns")
    op.drop_table("commissions")
    op.drop_table("payments")
    op.drop_table("bookings")
    op.drop_table("logistics_providers")
