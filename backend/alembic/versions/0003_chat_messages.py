"""Phase 3 part 3: chat messages between a donor and the organisation that accepted
their donation. A thread is an accepted offer (matches.id); there is no thread table.

Append-only, enforced in application code (app.db.AppendOnly), not by triggers.

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | Sequence[str] | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "chat_messages",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("match_id", sa.Uuid(), nullable=False),
        sa.Column("sender_id", sa.Uuid(), nullable=False),
        sa.Column("sender", sa.String(length=32), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("body <> ''", name="ck_chat_messages_body_not_empty"),
        sa.ForeignKeyConstraint(["match_id"], ["matches.id"], name="fk_chat_messages_match_id_matches"),
        sa.ForeignKeyConstraint(["sender_id"], ["users.id"], name="fk_chat_messages_sender_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_chat_messages"),
    )
    op.create_index("ix_chat_messages_match_id_id", "chat_messages", ["match_id", "id"])


def downgrade() -> None:
    op.drop_table("chat_messages")
