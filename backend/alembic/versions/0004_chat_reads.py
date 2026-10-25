"""Phase 3 part 3: how far each participant has read each chat thread, so the API can
report unread message counts.

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | Sequence[str] | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "chat_reads",
        sa.Column("match_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("last_read_message_id", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["match_id"], ["matches.id"], name="fk_chat_reads_match_id_matches"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_chat_reads_user_id_users"),
        sa.ForeignKeyConstraint(
            ["last_read_message_id"], ["chat_messages.id"], name="fk_chat_reads_last_read_message_id_chat_messages"
        ),
        sa.PrimaryKeyConstraint("match_id", "user_id", name="pk_chat_reads"),
    )


def downgrade() -> None:
    op.drop_table("chat_reads")
