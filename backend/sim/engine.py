"""Runs synthetic donations through the real scoring, policy and lifecycle modules.

Each donation is offered to the top of its slate; an accepted offer ends it, a declined
one goes through the real rematch decision (re-offer, or escalate at the threshold). The
transitions are looked up in the real lifecycle table, so an edge that does not exist
raises rather than being simulated. Every offer's five factor values, as scoring computed
them, and its simulated response become one SyntheticOffer.

Not modelled: held capacity (every organisation starts empty), the donor's own choice of
organisation, timeouts and the sweeper. Those belong to the real system, not to the labels.
"""

import random
from dataclasses import replace
from math import exp

from app.constants import DonationAction
from app.domain import lifecycle, policy, scoring
from app.domain.learning import FACTORS, SyntheticOffer
from app.domain.scoring import DonationFacts, MatchingConfig, OrganisationFacts
from sim.truth import TRUE_MODEL, TrueModel
from sim.world import SimOrg, World


def _facts(org: SimOrg, donation: DonationFacts) -> OrganisationFacts:
    need = org.needs.get(donation.category)
    return OrganisationFacts(
        organization_id=org.id,
        name=org.name,
        latitude=org.latitude,
        longitude=org.longitude,
        verified=True,
        categories_accepted=org.categories,
        pickup_capable=org.pickup_capable,
        storage_capacity=org.storage_capacity,
        held_quantity=0,
        need_urgency=need[0] if need else None,
        need_quantity=need[1] if need else None,
        accepted_offers=org.accepted,
        decided_offers=org.decided,
    )


def _features(candidate: scoring.Candidate) -> tuple[float, ...]:
    values = {c.factor: c.value for c in candidate.components}
    return tuple(float(values[f]) for f in FACTORS)


def _acceptance_probability(features: tuple[float, ...], truth: TrueModel) -> float:
    z = truth.intercept + sum(truth.coefficients[f] * x for f, x in zip(FACTORS, features))
    return 1.0 / (1.0 + exp(-z))


def run(
    world: World,
    seed: int,
    *,
    truth: TrueModel = TRUE_MODEL,
    config: MatchingConfig | None = None,
) -> list[SyntheticOffer]:
    """Labelled offers for every donation in the world, in order. Deterministic for a seed."""
    config = config or MatchingConfig()
    rng = random.Random(seed)
    orgs = {org.id: org for org in world.orgs}
    labelled: list[SyntheticOffer] = []

    for donation_id, donation in world.donations:
        state = lifecycle.INITIAL_STATE
        excluded: frozenset = frozenset()
        declines = 0
        since_escalation = 0
        state = lifecycle.next_state(state, DonationAction.OFFER)

        while True:
            slate = scoring.rank(
                donation,
                [_facts(o, donation) for o in orgs.values()],
                excluded,
                policy.effective_radius_km(declines, config),
                config,
            )
            top = slate.top()
            if top is None:
                break  # nothing to offer: the real system escalates this, outside the labels

            features = _features(top)
            accepted = rng.random() < _acceptance_probability(features, truth)
            labelled.append(SyntheticOffer(donation_id, top.organization_id, features, accepted))
            org = orgs[top.organization_id]
            orgs[org.id] = replace(org, decided=org.decided + 1, accepted=org.accepted + int(accepted))

            if accepted:
                state = lifecycle.next_state(state, DonationAction.ACCEPT)
                break

            state = lifecycle.next_state(state, DonationAction.REJECT)
            excluded = excluded | {top.organization_id}
            declines += 1
            since_escalation += 1
            remaining = scoring.rank(
                donation,
                [_facts(o, donation) for o in orgs.values()],
                excluded,
                policy.effective_radius_km(declines, config),
                config,
            )
            decision = policy.rematch_decision(
                declines_since_escalation=since_escalation, slate_empty=remaining.is_empty
            )
            state = lifecycle.next_state(state, decision.action)
            if decision.action == DonationAction.ESCALATE:
                break

    return labelled


__all__ = ["run"]
