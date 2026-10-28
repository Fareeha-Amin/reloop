"""Impact records (estimates), and donations that have no condition.

- impact_records: one append-only row per COMPLETED (reuse) or RECYCLED donation.
- donations.condition becomes nullable: a donation sent straight to recycling may have
  no condition (the donor may not know it). Every other donation keeps one.

Data backfill: every donation already COMPLETED or RECYCLED gets its impact record now,
so the dashboards are correct from the moment this ships (same approach as 0005). The
backfill uses the same pure rules as the live path (app.domain.impact), so a backfilled
record is identical to one the transition would have written, and its per-item factors
are snapshotted from the constants as they are on the day this runs.

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-28
"""

from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

from app.constants import Category, DonationStatus, ImpactOutcome, OfferResponse
from app.domain import impact as rules

revision: str = "0006"
down_revision: str | Sequence[str] | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("donations", "condition", existing_type=sa.String(length=32), nullable=True)

    op.create_table(
        "impact_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("donation_id", sa.Uuid(), nullable=False),
        sa.Column("donor_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=True),
        sa.Column("outcome", sa.String(length=32), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("mass_kg_per_item", sa.Numeric(precision=10, scale=3), nullable=False),
        sa.Column("mass_kg", sa.Numeric(precision=12, scale=3), nullable=False),
        sa.Column("carbon_kg_per_item", sa.Numeric(precision=10, scale=3), nullable=True),
        sa.Column("carbon_kg", sa.Numeric(precision=12, scale=3), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["donation_id"], ["donations.id"], name="fk_impact_records_donation_id_donations"),
        sa.ForeignKeyConstraint(["donor_id"], ["users.id"], name="fk_impact_records_donor_id_users"),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organization_profiles.id"],
            name="fk_impact_records_organization_id_organization_profiles",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_impact_records"),
        sa.UniqueConstraint("donation_id", name="uq_impact_records_donation_id"),
    )
    op.create_index("ix_impact_records_donor_id", "impact_records", ["donor_id"])
    op.create_index("ix_impact_records_organization_id", "impact_records", ["organization_id"])

    # --- Backfill: one record per donation already COMPLETED or RECYCLED. -------------------
    conn = op.get_bind()
    finished = conn.execute(
        sa.text(
            """
            SELECT d.id, d.donor_id, d.category, d.quantity, d.status,
                   (SELECT e.created_at FROM status_events e
                     WHERE e.donation_id = d.id AND e.to_state = d.status
                     ORDER BY e.id DESC LIMIT 1) AS finished_at,
                   (SELECT m.organization_id FROM matches m
                     WHERE m.donation_id = d.id AND m.response = :accepted
                     ORDER BY m.responded_at DESC LIMIT 1) AS organization_id
            FROM donations d
            WHERE d.status IN :finished_states
            """
        ).bindparams(sa.bindparam("finished_states", expanding=True)),
        {
            "accepted": OfferResponse.ACCEPTED.value,
            "finished_states": [s.value for s in (DonationStatus.COMPLETED, DonationStatus.RECYCLED)],
        },
    ).fetchall()
    for donation_id, donor_id, category, quantity, status, finished_at, organization_id in finished:
        outcome = rules.outcome_for(DonationStatus(status))
        est = rules.estimate(Category(category), quantity, outcome)
        conn.execute(
            sa.text(
                """
                INSERT INTO impact_records (id, donation_id, donor_id, organization_id, outcome, category,
                    quantity, mass_kg_per_item, mass_kg, carbon_kg_per_item, carbon_kg, created_at)
                VALUES (gen_random_uuid(), :donation_id, :donor_id, :organization_id, :outcome, :category,
                    :quantity, :mass_kg_per_item, :mass_kg, :carbon_kg_per_item, :carbon_kg, :at)
                """
            ),
            {
                "donation_id": donation_id,
                "donor_id": donor_id,
                "organization_id": organization_id if outcome == ImpactOutcome.REUSED else None,
                "outcome": outcome.value,
                "category": category,
                "quantity": quantity,
                "mass_kg_per_item": est.mass_kg_per_item,
                "mass_kg": est.mass_kg,
                "carbon_kg_per_item": est.carbon_kg_per_item,
                "carbon_kg": est.carbon_kg,
                "at": finished_at or datetime.now(UTC),
            },
        )


def downgrade() -> None:
    # A donation sent to recycling has no condition, which the old column cannot hold.
    # Refuse rather than invent a value or delete the donation.
    conn = op.get_bind()
    without_condition = conn.execute(
        sa.text("SELECT count(*) FROM donations WHERE condition IS NULL")
    ).scalar_one()
    if without_condition:
        raise RuntimeError(
            f"{without_condition} donation(s) were sent to recycling without a condition; "
            "downgrading would require inventing one. Resolve them first."
        )
    op.drop_index("ix_impact_records_organization_id", table_name="impact_records")
    op.drop_index("ix_impact_records_donor_id", table_name="impact_records")
    op.drop_table("impact_records")
    op.alter_column("donations", "condition", existing_type=sa.String(length=32), nullable=False)
