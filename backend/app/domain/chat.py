"""Who may read and write a donor-organisation chat thread (pure; no database).

A thread belongs to one accepted offer (a Match answered ACCEPTED). Two facts decide
access: the donation's status, and whether the thread's offer is the donation's latest
acceptance (after an admin requeue, another organisation's acceptance replaces it).

- The donor reads every thread on their own donation (the caller checks ownership).
- The organisation reads its thread while its offer is the latest acceptance; once
  another organisation accepts the donation, the earlier one loses the thread.
- Both may write while the thread is open: from acceptance onward, while the
  organisation holds the donation, and after it completes it. The thread closes only
  when the organisation stops holding the donation without completing it.
- Admins have no access to chats.
"""

from dataclasses import dataclass

from app.constants import Actor, ChatClosure, DonationStatus
from app.domain import lifecycle

# The holder's states, plus COMPLETED: the one state the holder itself moves the donation
# to (CONFIRM_RECEIPT). Any other way out of HELD_STATES (a stall to the admin queue, then
# a requeue, cancellation or recycling) closes the thread.
OPEN_STATES: frozenset[DonationStatus] = lifecycle.HELD_STATES | {DonationStatus.COMPLETED}


@dataclass(frozen=True)
class ThreadAccess:
    can_read: bool
    can_write: bool
    # Set when the thread is readable but closed.
    closed_reason: ChatClosure | None


NO_ACCESS = ThreadAccess(can_read=False, can_write=False, closed_reason=None)


def is_open(status: DonationStatus, is_current_acceptance: bool) -> bool:
    return is_current_acceptance and status in OPEN_STATES


def access(viewer: Actor, status: DonationStatus, is_current_acceptance: bool) -> ThreadAccess:
    """Access for `viewer` (DONOR: the donation's own donor; ACCEPTOR: the thread's own
    organisation) to a thread whose offer is, or is not, the latest acceptance."""
    if viewer == Actor.DONOR:
        can_read = True
    elif viewer == Actor.ACCEPTOR:
        can_read = is_current_acceptance
    else:
        return NO_ACCESS
    if not can_read:
        return NO_ACCESS
    open_ = is_open(status, is_current_acceptance)
    return ThreadAccess(
        can_read=True,
        can_write=open_,
        closed_reason=None if open_ else ChatClosure.NO_LONGER_HELD,
    )
