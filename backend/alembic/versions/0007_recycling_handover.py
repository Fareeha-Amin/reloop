"""Recycling handover step.

A donation sent to recycling (WASTE_REDIRECTED) now needs the donor's own handover to
the assigned recycler — drop-off, or a simulated platform pickup — before an admin can
confirm on the recycler's behalf (RECYCLING_IN_TRANSIT, a new lifecycle state). There is
no recycler login, so nobody else can attest that the goods arrived; CONFIRM_RECYCLED no
longer has an edge directly from WASTE_REDIRECTED (a deliberate change; see CLAUDE.md).

Schema change: handovers.match_id becomes nullable, and handovers gains a nullable
recycling_id (unique, FK to recyclings.id), so a Handover can belong either to an
accepted offer or to a recycling assignment. A CHECK constraint enforces exactly one of
the two is set — the one DB constraint that repeats an app-level rule, because it
protects an invariant across two nullable foreign keys, not a vocabulary value.

No data backfill: no row exists yet with recycling_id set, and no WASTE_REDIRECTED row
can be confirmed until this ships and its donor records a handover.

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | Sequence[str] | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("handovers", "match_id", existing_type=sa.Uuid(), nullable=True)
    op.add_column("handovers", sa.Column("recycling_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_handovers_recycling_id_recyclings", "handovers", "recyclings", ["recycling_id"], ["id"]
    )
    op.create_unique_constraint("uq_handovers_recycling_id", "handovers", ["recycling_id"])
    op.create_check_constraint(
        "handover_exactly_one_of_match_or_recycling",
        "handovers",
        "(match_id IS NULL) != (recycling_id IS NULL)",
    )


def downgrade() -> None:
    conn = op.get_bind()
    recycler_handovers = conn.execute(
        sa.text("SELECT count(*) FROM handovers WHERE recycling_id IS NOT NULL")
    ).scalar_one()
    if recycler_handovers:
        raise RuntimeError(
            f"{recycler_handovers} handover(s) are recorded against a recycling, which the "
            "old schema cannot represent. Resolve them first."
        )
    op.drop_constraint("handover_exactly_one_of_match_or_recycling", "handovers", type_="check")
    op.drop_constraint("uq_handovers_recycling_id", "handovers", type_="unique")
    op.drop_constraint("fk_handovers_recycling_id_recyclings", "handovers", type_="foreignkey")
    op.drop_column("handovers", "recycling_id")
    op.alter_column("handovers", "match_id", existing_type=sa.Uuid(), nullable=False)
