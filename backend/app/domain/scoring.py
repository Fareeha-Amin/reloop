"""Candidate ranking: hard filters, then a weighted sum of factors (non-negotiables 5, 11).

Pure: callers supply plain facts about the donation and each organisation, and get back
a ranked slate in which every score is decomposed into its components (factor, raw
value, factor value, weight, contribution). Reasons are structured data, not sentences,
so a client can render or translate them.

The weights are assigned, not learned (app.constants.SCORE_WEIGHTS): a new platform has
no accept/reject history to learn from. Donor rating is not a factor until reviews exist.

Boosts never touch these scores (see app.domain.policy): a multiplier applied to one
donation's candidates would not change their order.
"""

import hashlib
import json
import math
import uuid
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from app.constants import (
    ACCEPTANCE_PRIOR_RATE,
    ACCEPTANCE_PRIOR_WEIGHT,
    MAX_RADIUS_KM,
    PRIORITY_BOOST,
    RADIUS_CAP_KM,
    RADIUS_STEP,
    REJECTION_BOOST_CAP,
    REJECTION_BOOST_ENABLED,
    REJECTION_BOOST_STEP,
    SCORE_WEIGHTS,
    URGENCY_FACTOR,
    Category,
    FilterReason,
    ScoreFactor,
    Urgency,
)
from app.domain.geo import haversine_km


@dataclass(frozen=True)
class MatchingConfig:
    """Every tunable that affects ranking, queue priority or reach. Defaults come from
    app.constants; the simulation harness passes variants (e.g. the boost switched off)."""

    weights: Mapping[ScoreFactor, float] = field(default_factory=lambda: MappingProxyType(dict(SCORE_WEIGHTS)))
    urgency_factor: Mapping[Urgency, float] = field(default_factory=lambda: MappingProxyType(dict(URGENCY_FACTOR)))
    acceptance_prior_rate: float = ACCEPTANCE_PRIOR_RATE
    acceptance_prior_weight: float = ACCEPTANCE_PRIOR_WEIGHT
    max_radius_km: float = MAX_RADIUS_KM
    rejection_boost_enabled: bool = REJECTION_BOOST_ENABLED
    rejection_boost_step: float = REJECTION_BOOST_STEP
    rejection_boost_cap: float = REJECTION_BOOST_CAP
    radius_step: float = RADIUS_STEP
    radius_cap_km: float = RADIUS_CAP_KM
    priority_boost: float = PRIORITY_BOOST

    def __post_init__(self) -> None:
        if set(self.weights) != set(ScoreFactor):
            raise ValueError("weights must cover exactly the ScoreFactor values.")
        if not math.isclose(sum(self.weights.values()), 1.0, abs_tol=1e-9):
            raise ValueError("weights must sum to 1.")
        if any(w < 0 for w in self.weights.values()):
            raise ValueError("weights must be non-negative.")

    def as_dict(self) -> dict:
        """JSON-ready, with stable key order, stored with every ranking run."""
        return {
            "weights": {f.value: self.weights[f] for f in ScoreFactor},
            "urgency_factor": {u.value: self.urgency_factor[u] for u in Urgency},
            "acceptance_prior_rate": self.acceptance_prior_rate,
            "acceptance_prior_weight": self.acceptance_prior_weight,
            "max_radius_km": self.max_radius_km,
            "rejection_boost_enabled": self.rejection_boost_enabled,
            "rejection_boost_step": self.rejection_boost_step,
            "rejection_boost_cap": self.rejection_boost_cap,
            "radius_step": self.radius_step,
            "radius_cap_km": self.radius_cap_km,
            "priority_boost": self.priority_boost,
        }

    def version(self) -> str:
        """A fingerprint of the configuration: equal configs give equal versions."""
        canonical = json.dumps(self.as_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode()).hexdigest()[:12]


@dataclass(frozen=True)
class DonationFacts:
    category: Category
    quantity: int
    latitude: float
    longitude: float


@dataclass(frozen=True)
class OrganisationFacts:
    organization_id: uuid.UUID
    name: str
    latitude: float
    longitude: float
    verified: bool
    categories_accepted: frozenset[Category]
    pickup_capable: bool
    storage_capacity: int  # items
    held_quantity: int  # items in donations it currently holds (lifecycle.HELD_STATES)
    need_urgency: Urgency | None  # its active need in the donation's category, if any
    need_quantity: int | None
    accepted_offers: int  # offers it accepted
    decided_offers: int  # offers it accepted, rejected or let expire

    @property
    def remaining_capacity(self) -> int:
        return self.storage_capacity - self.held_quantity


@dataclass(frozen=True)
class Component:
    factor: ScoreFactor
    raw: float | str | None  # the underlying fact (km, urgency, items, observed rate)
    value: float  # the factor value, in [0, 1]
    weight: float
    contribution: float  # weight * value


@dataclass(frozen=True)
class Candidate:
    rank: int
    organization_id: uuid.UUID
    organization_name: str
    pickup_capable: bool
    distance_km: float
    score: float
    components: tuple[Component, ...]


@dataclass(frozen=True)
class Slate:
    radius_km: float
    candidates: tuple[Candidate, ...]
    filtered_out: Mapping[FilterReason, int]

    @property
    def is_empty(self) -> bool:
        return not self.candidates

    def top(self) -> Candidate | None:
        return self.candidates[0] if self.candidates else None

    def find(self, organization_id: uuid.UUID) -> Candidate | None:
        return next((c for c in self.candidates if c.organization_id == organization_id), None)


def hard_filter(
    donation: DonationFacts,
    org: OrganisationFacts,
    distance_km: float,
    radius_km: float,
    excluded: frozenset[uuid.UUID],
) -> FilterReason | None:
    """The first hard filter the organisation fails, or None if it is eligible."""
    if not org.verified:
        return FilterReason.NOT_VERIFIED
    if donation.category not in org.categories_accepted:
        return FilterReason.CATEGORY_NOT_ACCEPTED
    if org.organization_id in excluded:
        return FilterReason.EXCLUDED
    if distance_km > radius_km:
        return FilterReason.OUT_OF_RADIUS
    if org.remaining_capacity < donation.quantity:
        return FilterReason.INSUFFICIENT_CAPACITY
    return None


def acceptance_rate(accepted: int, decided: int, config: MatchingConfig) -> float:
    """Smoothed toward the prior, so an organisation with no history scores the prior."""
    w = config.acceptance_prior_weight
    return (accepted + w * config.acceptance_prior_rate) / (decided + w)


def score_components(
    org: OrganisationFacts, distance_km: float, radius_km: float, config: MatchingConfig
) -> tuple[Component, ...]:
    """Each factor in [0, 1]. Assumes the organisation passed the hard filters."""
    headroom = org.remaining_capacity / org.storage_capacity if org.storage_capacity > 0 else 0.0
    values: dict[ScoreFactor, tuple[float | str | None, float]] = {
        ScoreFactor.PROXIMITY: (round(distance_km, 3), max(0.0, 1.0 - distance_km / radius_km)),
        ScoreFactor.NEED_MATCH: (org.need_quantity, 1.0 if org.need_urgency is not None else 0.0),
        ScoreFactor.URGENCY: (
            org.need_urgency.value if org.need_urgency is not None else None,
            config.urgency_factor[org.need_urgency] if org.need_urgency is not None else 0.0,
        ),
        ScoreFactor.CAPACITY_HEADROOM: (org.remaining_capacity, min(1.0, max(0.0, headroom))),
        ScoreFactor.ACCEPTANCE_RATE: (
            round(org.accepted_offers / org.decided_offers, 4) if org.decided_offers else None,
            acceptance_rate(org.accepted_offers, org.decided_offers, config),
        ),
    }
    return tuple(
        Component(
            factor=factor,
            raw=raw,
            value=round(value, 6),
            weight=config.weights[factor],
            contribution=round(config.weights[factor] * value, 6),
        )
        for factor, (raw, value) in ((f, values[f]) for f in ScoreFactor)
    )


def rank(
    donation: DonationFacts,
    organisations: Iterable[OrganisationFacts],
    excluded: frozenset[uuid.UUID],
    radius_km: float,
    config: MatchingConfig,
) -> Slate:
    """Filter, score and order. Ties break on distance, then organisation id, so the
    same inputs always give the same slate."""
    filtered: Counter[FilterReason] = Counter()
    scored = []
    for org in organisations:
        distance = haversine_km(donation.latitude, donation.longitude, org.latitude, org.longitude)
        reason = hard_filter(donation, org, distance, radius_km, excluded)
        if reason is not None:
            filtered[reason] += 1
            continue
        components = score_components(org, distance, radius_km, config)
        score = round(sum(c.contribution for c in components), 6)
        scored.append((org, distance, score, components))

    scored.sort(key=lambda item: (-item[2], item[1], str(item[0].organization_id)))
    candidates = tuple(
        Candidate(
            rank=i,
            organization_id=org.organization_id,
            organization_name=org.name,
            pickup_capable=org.pickup_capable,
            distance_km=round(distance, 3),
            score=score,
            components=components,
        )
        for i, (org, distance, score, components) in enumerate(scored, start=1)
    )
    return Slate(
        radius_km=radius_km,
        candidates=candidates,
        filtered_out=MappingProxyType({r: filtered[r] for r in FilterReason if filtered[r]}),
    )
