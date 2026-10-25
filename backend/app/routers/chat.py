import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, status

from app.schemas.chat import ChatMessageIn, ChatReadIn, ChatThreadOut
from app.security.deps import DbSession, DonorOrAcceptorUser
from app.services import chat

router = APIRouter(prefix="/chats", tags=["chat"])


@router.get("", response_model=list[ChatThreadOut])
def list_threads(donation_id: uuid.UUID, user: DonorOrAcceptorUser, db: DbSession):
    """The chat threads on a donation that you can read, newest acceptance first, each
    with its messages. A thread is one accepted offer: the donor reads every thread on
    their donation; the organisation reads its own while its acceptance is the latest.
    Both can write from acceptance onward, including after completion; a thread closes
    (closed_reason) only when the organisation stops holding the donation without
    completing it. Admins have no access to chats. Poll it: there is no push."""
    return chat.threads_out(db, user, chat.threads_for_donation(db, user, donation_id))


@router.post("/{thread_id}/messages", response_model=ChatThreadOut, status_code=status.HTTP_201_CREATED)
def post_message(thread_id: uuid.UUID, data: ChatMessageIn, user: DonorOrAcceptorUser, db: DbSession):
    """Append a message (messages are never edited or deleted). 409 if the thread is
    closed. Returns the whole thread."""
    view = chat.post_message(db, user, thread_id, data.body, datetime.now(UTC))
    return chat.threads_out(db, user, [view])[0]


@router.post("/{thread_id}/read", response_model=ChatThreadOut)
def mark_read(thread_id: uuid.UUID, data: ChatReadIn, user: DonorOrAcceptorUser, db: DbSession):
    """You have been shown the thread up to `up_to_message_id`: messages from the other
    party up to it stop counting as unread (`unread` here, and `chat.unread` on the
    donation). Read state is kept per user on the server; it never moves backward.
    Works on closed threads too."""
    view = chat.mark_read(db, user, thread_id, data.up_to_message_id, datetime.now(UTC))
    return chat.threads_out(db, user, [view])[0]
