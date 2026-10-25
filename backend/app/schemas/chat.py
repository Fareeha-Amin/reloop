"""Donor-organisation chat. A thread is one accepted offer; its id is the offer's id."""

import uuid
from datetime import datetime
from typing import Annotated

from pydantic import Field, StringConstraints

from app.constants import CHAT_MESSAGE_MAX_LENGTH, Actor, ChatClosure
from app.schemas.common import InputModel, OutputModel

ChatBody = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=CHAT_MESSAGE_MAX_LENGTH)
]


class ChatMessageIn(InputModel):
    body: ChatBody


class ChatMessageOut(OutputModel):
    id: int = Field(description="Increases within a thread.")
    at: datetime
    sender: Actor = Field(description="DONOR or ACCEPTOR: which side of the thread wrote it.")
    sender_name: str | None = Field(
        description="The organisation's name for its messages. Null for the donor's: the donor's "
        "name is not disclosed to the organisation."
    )
    mine: bool = Field(description="Written by the user reading the thread.")
    body: str
    notification_key: str | None = Field(
        description="The key of the notification this message produced for the reader (messages "
        "from the other party only), so a client can mark it read when the thread is shown."
    )


class ChatReadIn(InputModel):
    up_to_message_id: int = Field(description="The newest message the reader has been shown, in this thread.")


class ChatThreadOut(OutputModel):
    id: uuid.UUID = Field(description="The thread: the accepted offer's id. Post to /chats/{id}/messages.")
    donation_id: uuid.UUID
    organization_name: str
    accepted_at: datetime
    can_write: bool
    closed_reason: ChatClosure | None = Field(
        description="Why the thread no longer takes messages, when can_write is false."
    )
    unread: int = Field(description="Messages from the other party the reader has not marked read.")
    messages: list[ChatMessageOut] = Field(description="Oldest first.")


class ChatSummaryOut(OutputModel):
    """On a donation, for its donor or the organisation that accepted it: present only
    when the viewer can read at least one chat thread on it."""

    threads: int = Field(description="Threads the viewer can read (more than one after an admin requeue).")
    unread: int = Field(description="Unread messages from the other party, across those threads.")
    can_write: bool = Field(description="Whether one of them still takes messages.")
