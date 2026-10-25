"""Donor-organisation chat: who can read and write a thread, in each state."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.constants import CHAT_MESSAGE_MAX_LENGTH, STALL_TIMEOUTS, DonationStatus
from app.db import AppendOnlyViolation
from app.models import ChatMessage
from app.services import sweeper
from tests.api import helpers as h


def _threads(client, headers, donation_id) -> list[dict]:
    resp = client.get("/chats", headers=headers, params={"donation_id": donation_id})
    assert resp.status_code == 200, resp.text
    return resp.json()


def _list_status(client, headers, donation_id) -> int:
    return client.get("/chats", headers=headers, params={"donation_id": donation_id}).status_code


def _post(client, headers, thread_id, body="Hello"):
    return client.post(f"/chats/{thread_id}/messages", headers=headers, json={"body": body})


def _says(client, headers, thread_id, body) -> dict:
    resp = _post(client, headers, thread_id, body)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _can_write(client, headers, donation_id) -> list[bool]:
    return [t["can_write"] for t in _threads(client, headers, donation_id)]


def _stall(db, donation_id):
    later = datetime.now(UTC) + STALL_TIMEOUTS[DonationStatus.ACCEPTED] + timedelta(minutes=1)
    sweeper.sweep(db, later)
    db.expire_all()


@pytest.fixture
def accepted(client, db):
    """A donation accepted by organisation A (near the donor). B (further away) is
    verified too, so an admin requeue has somewhere to go."""
    donor = h.donor(client)
    a_headers, a_id = h.verified_acceptor(client, db, at=h.NEAR)
    b_headers, b_id = h.verified_acceptor(client, db, at=h.KORAMANGALA, name="Koramangala Shelter")
    donation = h.create_donation(client, donor)
    h.offer(client, donor, donation["id"], a_id)
    thread_id = h.accept(client, a_headers, donation["id"])["match_id"]
    return {"donor": donor, "a": a_headers, "b": b_headers, "id": donation["id"], "thread": thread_id}


def test_requires_donor_or_acceptor(client, db, accepted):
    assert client.get("/chats", params={"donation_id": accepted["id"]}).status_code == 401
    admin = h.admin(client, db)
    assert _list_status(client, admin, accepted["id"]) == 403
    assert _post(client, admin, accepted["thread"]).status_code == 403


def test_no_thread_before_acceptance(client, db):
    donor = h.donor(client)
    org_headers, org_id = h.verified_acceptor(client, db)
    donation = h.create_donation(client, donor)
    assert _threads(client, donor, donation["id"]) == []

    h.offer(client, donor, donation["id"], org_id)
    match_id = h.the_offer(client, org_headers, donation["id"])["match_id"]
    assert _threads(client, donor, donation["id"]) == []
    assert _list_status(client, org_headers, donation["id"]) == 404  # an open offer is not a thread
    assert _post(client, donor, match_id).status_code == 404
    assert _post(client, org_headers, match_id).status_code == 404


def test_a_rejected_offer_has_no_thread(client, db):
    donor = h.donor(client)
    org_headers, org_id = h.verified_acceptor(client, db)
    donation = h.create_donation(client, donor)
    h.offer(client, donor, donation["id"], org_id)
    match_id = h.reject(client, org_headers, donation["id"])["match_id"]
    assert _post(client, org_headers, match_id).status_code == 404
    assert _post(client, donor, match_id).status_code == 404
    assert _list_status(client, org_headers, donation["id"]) == 404


def test_both_sides_write_while_held_and_after_completion(client, accepted):
    donor, a, did, thread = accepted["donor"], accepted["a"], accepted["id"], accepted["thread"]
    path = f"/organisations/me/donations/{did}"

    _says(client, donor, thread, "Hi, the bags are by the door.")  # ACCEPTED
    _says(client, a, thread, "Thanks! We can come on Saturday.")
    when = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    assert client.post(f"{path}/schedule-pickup", headers=a, json={"scheduled_for": when}).status_code == 200
    _says(client, donor, thread, "Saturday works.")  # PICKUP_SCHEDULED
    assert client.post(f"/donations/{did}/mark-handed-over", headers=donor).status_code == 200
    _says(client, a, thread, "Collected.")  # IN_TRANSIT
    assert client.post(f"{path}/confirm-receipt", headers=a).json()["status"] == "COMPLETED"
    _says(client, donor, thread, "Glad they found a home.")  # COMPLETED: still open
    _says(client, a, thread, "The children loved them.")

    [donor_view] = _threads(client, donor, did)
    [org_view] = _threads(client, a, did)
    for view in (donor_view, org_view):
        assert view["id"] == thread and view["can_write"] is True and view["closed_reason"] is None
        assert view["organization_name"] == "Sunrise Children's Home"
        assert len(view["messages"]) == 6
    ids = [m["id"] for m in donor_view["messages"]]
    assert ids == sorted(ids)

    first, second = donor_view["messages"][:2]
    assert (first["sender"], first["mine"], first["sender_name"], first["notification_key"]) == (
        "DONOR", True, None, None
    )
    assert (second["sender"], second["mine"], second["sender_name"]) == ("ACCEPTOR", False, "Sunrise Children's Home")
    assert second["notification_key"] == f"CHAT_MESSAGE:{second['id']}"
    org_first = org_view["messages"][0]
    assert (org_first["mine"], org_first["sender_name"]) == (False, None)  # the donor's name is not disclosed


def test_outsiders_cannot_read_or_write(client, accepted):
    other_donor = h.donor(client)
    _says(client, accepted["donor"], accepted["thread"], "Private")
    for headers in (other_donor, accepted["b"]):
        assert _list_status(client, headers, accepted["id"]) == 404
        assert _post(client, headers, accepted["thread"]).status_code == 404


def test_a_stall_to_the_admin_queue_closes_the_thread_but_keeps_it_readable(client, db, accepted):
    donor, a, did, thread = accepted["donor"], accepted["a"], accepted["id"], accepted["thread"]
    _says(client, donor, thread, "Are you still coming?")
    _stall(db, did)
    assert h.status(client, donor, did)["status"] == "NEEDS_ADMIN"

    for headers in (donor, a):
        [view] = _threads(client, headers, did)
        assert (view["can_write"], view["closed_reason"]) == (False, "NO_LONGER_HELD")
        assert [m["body"] for m in view["messages"]] == ["Are you still coming?"]
        assert _post(client, headers, thread).status_code == 409


def test_admin_cancel_leaves_a_read_only_thread(client, db, accepted):
    _stall(db, accepted["id"])
    admin = h.admin(client, db)
    resp = client.post(f"/admin/donations/{accepted['id']}/cancel", headers=admin, json={"reason": "Donor moved"})
    assert resp.status_code == 200, resp.text
    assert _can_write(client, accepted["donor"], accepted["id"]) == [False]
    assert _can_write(client, accepted["a"], accepted["id"]) == [False]
    assert _post(client, accepted["donor"], accepted["thread"]).status_code == 409


def test_requeued_donation(client, db, accepted):
    """A accepts and stalls; an admin requeues it to B. A keeps a read-only thread until
    B accepts, then loses it; the donor keeps both, and only B's is open."""
    donor, a, b, did, a_thread = accepted["donor"], accepted["a"], accepted["b"], accepted["id"], accepted["thread"]
    _says(client, a, a_thread, "Our van broke down, sorry.")
    _stall(db, did)
    admin = h.admin(client, db)
    resp = client.post(f"/admin/donations/{did}/requeue", headers=admin, json={"reason": "Holder reneged"})
    assert resp.status_code == 200, resp.text
    assert h.status(client, donor, did)["status"] == "MATCHED"  # re-offered to B

    # Between the requeue and B's answer: A's acceptance is still the latest.
    assert _can_write(client, donor, did) == [False]
    [a_view] = _threads(client, a, did)
    assert (a_view["id"], a_view["can_write"]) == (a_thread, False)
    assert _post(client, a, a_thread).status_code == 409
    assert _list_status(client, b, did) == 404  # an open offer is not a thread
    assert _post(client, b, a_thread).status_code == 404

    b_thread = h.accept(client, b, did)["match_id"]
    donor_threads = _threads(client, donor, did)
    assert [(t["id"], t["can_write"]) for t in donor_threads] == [(b_thread, True), (a_thread, False)]
    assert donor_threads[0]["organization_name"] == "Koramangala Shelter"
    assert [m["body"] for m in donor_threads[1]["messages"]] == ["Our van broke down, sorry."]

    assert _list_status(client, a, did) == 404  # A has lost its thread
    assert _post(client, a, a_thread).status_code == 404
    assert _post(client, b, a_thread).status_code == 404  # B cannot read A's thread
    assert [t["id"] for t in _threads(client, b, did)] == [b_thread]
    _says(client, b, b_thread, "We can collect tomorrow.")
    _says(client, donor, b_thread, "Thank you!")
    assert _post(client, donor, a_thread).status_code == 409


@pytest.mark.parametrize("body", ["", "   ", "x" * (CHAT_MESSAGE_MAX_LENGTH + 1)])
def test_message_validation(client, accepted, body):
    assert _post(client, accepted["donor"], accepted["thread"], body).status_code == 422


def test_message_is_trimmed_and_may_be_the_maximum_length(client, accepted):
    longest = "y" * CHAT_MESSAGE_MAX_LENGTH
    thread = _says(client, accepted["donor"], accepted["thread"], f"  {longest}  ")
    assert thread["messages"][-1]["body"] == longest


def test_messages_are_never_edited_or_deleted(client, db, accepted):
    _says(client, accepted["donor"], accepted["thread"], "Original")
    db.expire_all()
    message = db.scalar(select(ChatMessage).where(ChatMessage.match_id == accepted["thread"]))
    message.body = "Rewritten"
    with pytest.raises(AppendOnlyViolation, match="immutable"):
        db.flush()
    db.rollback()
    message = db.scalar(select(ChatMessage).where(ChatMessage.match_id == accepted["thread"]))
    db.delete(message)
    with pytest.raises(AppendOnlyViolation, match="never deleted"):
        db.flush()
    db.rollback()


# --- The chat summary on donations, unread counts and read pointers ----------------------------


def _donor_chat(client, donor, donation_id):
    return h.status(client, donor, donation_id)["chat"]


def _org_chat(client, org, donation_id):
    resp = client.get(f"/organisations/me/donations/{donation_id}", headers=org)
    assert resp.status_code == 200, resp.text
    return resp.json()["chat"]


def _org_list_chat(client, org, donation_id):
    resp = client.get("/organisations/me/donations", headers=org)
    assert resp.status_code == 200, resp.text
    return next(d["chat"] for d in resp.json() if d["donation_id"] == donation_id)


def _read(client, headers, thread_id, up_to):
    return client.post(f"/chats/{thread_id}/read", headers=headers, json={"up_to_message_id": up_to})


def test_no_chat_summary_before_acceptance_or_for_admins(client, db):
    donor = h.donor(client)
    _, org_id = h.verified_acceptor(client, db)
    donation = h.create_donation(client, donor)
    assert donation["chat"] is None
    h.offer(client, donor, donation["id"], org_id)
    assert _donor_chat(client, donor, donation["id"]) is None
    admin = h.admin(client, db)
    assert client.get(f"/donations/{donation['id']}", headers=admin).json()["chat"] is None


def test_summary_counts_unread_messages_from_the_other_party_only(client, db, accepted):
    donor, a, did, thread = accepted["donor"], accepted["a"], accepted["id"], accepted["thread"]
    empty = {"threads": 1, "unread": 0, "can_write": True}
    assert _donor_chat(client, donor, did) == empty
    assert _org_chat(client, a, did) == empty

    _says(client, a, thread, "One")
    _says(client, a, thread, "Two")
    last = _says(client, donor, thread, "Hi")["messages"][-1]
    assert _donor_chat(client, donor, did)["unread"] == 2  # your own messages are never unread
    assert _org_chat(client, a, did)["unread"] == 1
    assert _org_list_chat(client, a, did)["unread"] == 1  # the dashboard list too
    donor_list = client.get("/donations", headers=donor).json()
    assert next(d for d in donor_list if d["id"] == did)["chat"]["unread"] == 2
    [thread_view] = _threads(client, donor, did)
    assert thread_view["unread"] == 2

    first_id = thread_view["messages"][0]["id"]
    assert _read(client, donor, thread, first_id).json()["unread"] == 1  # read up to "One"
    assert _read(client, donor, thread, last["id"]).json()["unread"] == 0
    assert _donor_chat(client, donor, did)["unread"] == 0
    assert _org_chat(client, a, did)["unread"] == 1  # each reader has their own pointer

    # The pointer never moves backward.
    assert _read(client, donor, thread, first_id).json()["unread"] == 0


def test_mark_read_access_and_validation(client, db, accepted):
    donor, a, b, thread = accepted["donor"], accepted["a"], accepted["b"], accepted["thread"]
    message_id = _says(client, a, thread, "Hello")["messages"][-1]["id"]
    other_donor = h.donor(client)
    assert _read(client, other_donor, thread, message_id).status_code == 404
    assert _read(client, b, thread, message_id).status_code == 404
    assert _read(client, h.admin(client, db), thread, message_id).status_code == 403
    assert _read(client, donor, thread, 10**12).status_code == 422  # no such message

    # A message from another thread is refused.
    donor2 = h.donor(client)
    a2_headers, a2_id = h.verified_acceptor(client, db, at=h.NEAR)
    other = h.create_donation(client, donor2)
    h.offer(client, donor2, other["id"], a2_id)
    other_thread = h.accept(client, a2_headers, other["id"])["match_id"]
    foreign = _says(client, donor2, other_thread, "Elsewhere")["messages"][-1]["id"]
    assert _read(client, donor, thread, foreign).status_code == 422


def test_closed_threads_can_still_be_marked_read(client, db, accepted):
    donor, a, did, thread = accepted["donor"], accepted["a"], accepted["id"], accepted["thread"]
    message_id = _says(client, a, thread, "Sorry, we can't come")["messages"][-1]["id"]
    _stall(db, did)
    assert _donor_chat(client, donor, did) == {"threads": 1, "unread": 1, "can_write": False}
    assert _read(client, donor, thread, message_id).json()["unread"] == 0


def test_summary_after_a_requeue(client, db, accepted):
    donor, a, b, did = accepted["donor"], accepted["a"], accepted["b"], accepted["id"]
    _says(client, a, accepted["thread"], "Van broke down")
    _stall(db, did)
    admin = h.admin(client, db)
    client.post(f"/admin/donations/{did}/requeue", headers=admin, json={"reason": "Holder reneged"})
    b_thread = h.accept(client, b, did)["match_id"]
    _says(client, b, b_thread, "We'll collect")

    assert _donor_chat(client, donor, did) == {"threads": 2, "unread": 2, "can_write": True}
    assert _org_chat(client, b, did) == {"threads": 1, "unread": 0, "can_write": True}
    assert all(d["donation_id"] != did for d in client.get("/organisations/me/donations", headers=a).json())
