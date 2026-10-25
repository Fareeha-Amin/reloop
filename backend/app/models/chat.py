import uuid
from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.constants import Actor
from app.db import AppendOnly, Base, StrEnumType


class ChatMessage(AppendOnly, Base):
    """One message in a donor-organisation chat thread. A thread is an accepted offer
    (match_id): no thread table. Who may read and write is decided by app.domain.chat.

    Append-only: messages are never edited or deleted. The key is a sequence, like
    status_events: messages are listed in order within a thread whose access is checked,
    and never addressed by id on their own."""

    __tablename__ = "chat_messages"
    __table_args__ = (
        Index("ix_chat_messages_match_id_id", "match_id", "id"),
        # Length is validated at the API (CHAT_MESSAGE_MAX_LENGTH); this repeats no constant.
        CheckConstraint("body <> ''", name="body_not_empty"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    match_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("matches.id"))
    sender_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    # DONOR or ACCEPTOR: which side of the thread wrote it.
    sender: Mapped[Actor] = mapped_column(StrEnumType(Actor))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ChatRead(Base):
    """How far one participant has read one thread: the newest message they have seen.
    Unread = messages from the other party with a larger id. A pointer that only moves
    forward (app.services.chat.mark_read), so it is updated in place, not append-only:
    it records no history worth keeping."""

    __tablename__ = "chat_reads"

    match_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("matches.id"), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    last_read_message_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("chat_messages.id"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
