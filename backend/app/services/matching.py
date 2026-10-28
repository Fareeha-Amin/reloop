"""Matching against the database: gathers plain facts for app.domain.scoring, stores
ranking runs and offers, and resolves RE_MATCHING.

The exclusion list, decline count and escalation history are all derived from Match
rows and StatusEvents; none of them is stored on Donation.
"""

import uuid
from collections import defaultdict
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import distinct_on
from sqlalchemy.orm import Session

from app.constants import (
    OFFER_TTL,
    Actor,
    DonationAction,
    EscalationCause,
    OfferResponse,
    OfferSource,
    RankingTrigger,
    VerificationStatus,
)
from app.domain import lifecycle, policy, scoring
from app.domain.scoring import Candidate, MatchingConfig, Slate
from app.models import CurrentNeed, Donation, Match, OrganizationProfile, RankingRun, StatusEvent
from app.services import training, transitions

# The cold-start prior: SCORE_WEIGHTS and the other defaults. Rankings use
# training.active_config(db), which is this until a fit is activated.
DEFAULT_CONFIG = MatchingConfig()


# --- Derived facts ------------------------------------------------------------------------


def declines(db: Session, donation_id: uuid.UUID) -> int:
    return db.scalar(
        select(func.count())
        .select_from(Match)
        .where(Match.donation_id == donation_id, Match.response.in_(policy.DECLINE_RESPONSES))
    )


def declines_by_donation(db: Session, donation_ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
    if not donation_ids:
        return {}
    rows = db.execute(
        select(Match.donation_id, func.count())
        .where(Match.donation_id.in_(donation_ids), Match.response.in_(policy.DECLINE_RESPONSES))
        .group_by(Match.donation_id)
    )
    return dict(rows.all())


def last_escalated_at(db: Session, donation_id: uuid.UUID) -> datetime | None:
    return db.scalar(
        select(func.max(StatusEvent.created_at)).where(
            StatusEvent.donation_id == donation_id, StatusEvent.action == DonationAction.ESCALATE
        )
    )


def declines_since_last_escalation(db: Session, donation_id: uuid.UUID) -> int:
    """Declines answered after the most recent escalation. Escalation is not a Match, so
    its time comes from the (append-only) StatusEvent log."""
    query = select(func.count()).select_from(Match).where(
        Match.donation_id == donation_id, Match.response.in_(policy.DECLINE_RESPONSES)
    )
    since = last_escalated_at(db, donation_id)
    if since is not None:
        query = query.where(Match.responded_at > since)
    return db.scalar(query)


def latest_escalation_cause(db: Session, donation_id: uuid.UUID) -> EscalationCause | None:
    return db.scalar(
        select(StatusEvent.cause)
        .where(StatusEvent.donation_id == donation_id, StatusEvent.action == DonationAction.ESCALATE)
        .order_by(StatusEvent.id.desc())
        .limit(1)
    )


def acceptor_pickup_chosen(db: Session, match_id: uuid.UUID) -> bool:
    """Whether the donor has recorded CHOOSE_ACCEPTOR_COLLECTION for this acceptance
    (lifecycle's ACCEPTED -> ACCEPTED self-loop). Derived from the event log, never
    stored, the same way a decline count or an escalation cause already is."""
    return (
        db.scalar(
            select(StatusEvent.id)
            .where(StatusEvent.match_id == match_id, StatusEvent.action == DonationAction.CHOOSE_ACCEPTOR_COLLECTION)
            .limit(1)
        )
        is not None
    )


def excluded_organisations(db: Session, donation_id: uuid.UUID) -> frozenset[uuid.UUID]:
    """Every organisation ever offered this donation is excluded from it for good."""
    return frozenset(db.scalars(select(Match.organization_id).where(Match.donation_id == donation_id)))


def open_offer(db: Session, donation_id: uuid.UUID) -> Match | None:
    return db.scalar(select(Match).where(Match.donation_id == donation_id, Match.response.is_(None)))


def current_acceptance(db: Session, donation_id: uuid.UUID) -> Match | None:
    """The most recent accepted offer. For a donation in lifecycle.HELD_STATES, its
    organisation is the one holding the donation."""
    return db.scalar(
        select(Match)
        .where(Match.donation_id == donation_id, Match.response == OfferResponse.ACCEPTED)
        .order_by(Match.responded_at.desc())
        .limit(1)
    )


def holder(db: Session, donation: Donation) -> Match | None:
    """The accepted offer whose organisation holds the donation right now, if any."""
    if donation.status not in lifecycle.HELD_STATES:
        return None
    return current_acceptance(db, donation.id)


def held_quantities(db: Session, org_ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
    """Items each organisation currently holds: donations in HELD_STATES whose latest
    acceptance is theirs. Derived, so nothing ever decrements a counter."""
    if not org_ids:
        return {}
    latest = (
        select(Match.donation_id, Match.organization_id, Donation.quantity)
        .join(Donation, Donation.id == Match.donation_id)
        .where(Match.response == OfferResponse.ACCEPTED, Donation.status.in_(lifecycle.HELD_STATES))
        .order_by(Match.donation_id, Match.responded_at.desc())
        .ext(distinct_on(Match.donation_id))
    )
    totals: dict[uuid.UUID, int] = defaultdict(int)
    for _, org_id, quantity in db.execute(latest):
        if org_id in org_ids:
            totals[org_id] += quantity
    return totals


def acceptance_stats(db: Session, org_ids: list[uuid.UUID]) -> dict[uuid.UUID, tuple[int, int]]:
    """{org: (accepted, decided)} over all offers it has answered or let expire."""
    if not org_ids:
        return {}
    accepted = func.count().filter(Match.response == OfferResponse.ACCEPTED)
    rows = db.execute(
        select(Match.organization_id, accepted, func.count())
        .where(Match.organization_id.in_(org_ids), Match.response.in_(policy.DECIDED_RESPONSES))
        .group_by(Match.organization_id)
    )
    return {org_id: (int(a), int(d)) for org_id, a, d in rows}


def organisation_facts(db: Session, donation: Donation) -> list[scoring.OrganisationFacts]:
    """Every organisation accepting the donation's category (verified or not, so the
    slate can report how many the verification filter removed)."""
    orgs = list(
        db.scalars(
            select(OrganizationProfile).where(
                OrganizationProfile.categories_accepted.contains([donation.category])
            )
        )
    )
    ids = [o.id for o in orgs]
    held = held_quantities(db, ids)
    stats = acceptance_stats(db, ids)
    needs = {
        n.organization_id: n
        for n in db.scalars(
            select(CurrentNeed).where(
                CurrentNeed.organization_id.in_(ids),
                CurrentNeed.category == donation.category,
                CurrentNeed.is_active.is_(True),
            )
        )
    }
    facts = []
    for org in orgs:
        need = needs.get(org.id)
        accepted, decided = stats.get(org.id, (0, 0))
        facts.append(
            scoring.OrganisationFacts(
                organization_id=org.id,
                name=org.name,
                latitude=org.latitude,
                longitude=org.longitude,
                verified=org.verification_status == VerificationStatus.VERIFIED,
                categories_accepted=frozenset(org.categories_accepted),
                pickup_capable=org.pickup_capable,
                storage_capacity=org.storage_capacity,
                held_quantity=held.get(org.id, 0),
                need_urgency=need.urgency if need else None,
                need_quantity=need.quantity_needed if need else None,
                accepted_offers=accepted,
                decided_offers=decided,
            )
        )
    return facts


def compute_slate(db: Session, donation: Donation, config: MatchingConfig | None = None) -> tuple[Slate, int]:
    """The donation's current eligible slate, and the decline count that set its radius.
    Ranked with the active configuration unless one is given (the simulation passes its own)."""
    config = config or training.active_config(db)
    n = declines(db, donation.id)
    slate = scoring.rank(
        scoring.DonationFacts(
            category=donation.category,
            quantity=donation.quantity,
            latitude=donation.pickup_latitude,
            longitude=donation.pickup_longitude,
        ),
        organisation_facts(db, donation),
        excluded_organisations(db, donation.id),
        policy.effective_radius_km(n, config),
        config,
    )
    return slate, n


# --- Runs and offers -----------------------------------------------------------------------


def candidate_json(c: Candidate) -> dict:
    return {
        "rank": c.rank,
        "organization_id": str(c.organization_id),
        "organization_name": c.organization_name,
        "pickup_capable": c.pickup_capable,
        "distance_km": c.distance_km,
        "score": c.score,
        "components": [
            {
                "factor": comp.factor.value,
                "raw": comp.raw,
                "value": comp.value,
                "weight": comp.weight,
                "contribution": comp.contribution,
            }
            for comp in c.components
        ],
    }


def store_run(
    db: Session,
    donation: Donation,
    slate: Slate,
    declines_count: int,
    trigger: RankingTrigger,
    now: datetime,
    config: MatchingConfig = DEFAULT_CONFIG,
) -> RankingRun:
    run = RankingRun(
        id=uuid.uuid4(),
        donation_id=donation.id,
        trigger=trigger,
        radius_km=slate.radius_km,
        declines=declines_count,
        config_version=config.version(),
        config=config.as_dict(),
        slate=[candidate_json(c) for c in slate.candidates],
        filtered_out={reason.value: n for reason, n in slate.filtered_out.items()},
        created_at=now,
    )
    db.add(run)
    return run


def make_offer(
    db: Session,
    donation: Donation,
    run: RankingRun,
    candidate: Candidate,
    source: OfferSource,
    now: datetime,
) -> Match:
    match = Match(
        id=uuid.uuid4(),
        donation_id=donation.id,
        organization_id=candidate.organization_id,
        ranking_run_id=run.id,
        rank=candidate.rank,
        offered_by=source,
        offered_at=now,
        expires_at=now + OFFER_TTL,
    )
    db.add(match)
    return match


def resolve_re_matching(db: Session, donation: Donation, now: datetime, config: MatchingConfig | None = None) -> None:
    """RE_MATCHING is transient: in the same transaction, re-offer to the new top
    candidate or escalate to the donor."""
    config = config or training.active_config(db)
    slate, n = compute_slate(db, donation, config)
    decision = policy.rematch_decision(
        declines_since_escalation=declines_since_last_escalation(db, donation.id),
        slate_empty=slate.is_empty,
    )
    if decision.action == DonationAction.REOFFER:
        run = store_run(db, donation, slate, n, RankingTrigger.RE_MATCHING, now, config)
        match = make_offer(db, donation, run, slate.top(), OfferSource.SYSTEM, now)
        transitions.apply(db, donation, DonationAction.REOFFER, Actor.SYSTEM, now, match=match)
        return
    if decision.cause == EscalationCause.NO_CANDIDATES:
        # The empty slate is the evidence for this escalation; keep it.
        store_run(db, donation, slate, n, RankingTrigger.RE_MATCHING, now, config)
    transitions.apply(db, donation, DonationAction.ESCALATE, Actor.SYSTEM, now, cause=decision.cause)


def organisation_may_see_images(db: Session, donation_id: uuid.UUID, org_id: uuid.UUID) -> bool:
    """While it has an open offer for the donation, or holds it."""
    donation = db.get(Donation, donation_id)
    if donation is None:
        return False
    offer = open_offer(db, donation_id)
    if offer is not None and offer.organization_id == org_id:
        return True
    held = holder(db, donation)
    return held is not None and held.organization_id == org_id
