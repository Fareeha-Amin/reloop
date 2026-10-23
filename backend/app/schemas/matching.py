"""Ranking slates and the inputs to lifecycle actions."""

import uuid
from typing import Annotated

from pydantic import AwareDatetime, Field, StringConstraints

from app.constants import NOTE_MAX_LENGTH, FilterReason, RejectReason, ScoreFactor
from app.domain.scoring import Candidate, Slate
from app.schemas.common import InputModel, Note, OutputModel


class ComponentOut(OutputModel):
    """One factor of a score. Structured, not a sentence, so a client can render or
    translate it: e.g. PROXIMITY, raw 2.1 (km), value 0.86, weight 0.3, contribution 0.258."""

    factor: ScoreFactor
    raw: float | str | None = Field(
        description="The underlying fact: km (PROXIMITY), items needed (NEED_MATCH), urgency "
        "(URGENCY), remaining items (CAPACITY_HEADROOM), observed rate or null if no history "
        "(ACCEPTANCE_RATE)."
    )
    value: float = Field(description="The factor value, in [0, 1].")
    weight: float
    contribution: float = Field(description="weight x value; the contributions sum to the score.")


class CandidateOut(OutputModel):
    rank: int
    organization_id: uuid.UUID
    organization_name: str
    pickup_capable: bool
    distance_km: float
    score: float
    components: list[ComponentOut]

    @classmethod
    def from_candidate(cls, c: Candidate) -> "CandidateOut":
        return cls(
            rank=c.rank,
            organization_id=c.organization_id,
            organization_name=c.organization_name,
            pickup_capable=c.pickup_capable,
            distance_km=c.distance_km,
            score=c.score,
            components=[ComponentOut.model_validate(comp, from_attributes=True) for comp in c.components],
        )


class SlateOut(OutputModel):
    """The donation's eligible organisations, best first. A preview: nothing is stored
    until an offer is made, which re-ranks and stores the slate it was made against."""

    radius_km: float = Field(description="Search radius; widens with each decline (capped).")
    declines: int
    config_version: str
    candidates: list[CandidateOut]
    filtered_out: dict[FilterReason, int] = Field(
        description="Organisations accepting this category that the hard filters removed, by reason."
    )

    @classmethod
    def from_slate(cls, slate: Slate, declines: int, config_version: str) -> "SlateOut":
        return cls(
            radius_km=slate.radius_km,
            declines=declines,
            config_version=config_version,
            candidates=[CandidateOut.from_candidate(c) for c in slate.candidates],
            filtered_out=dict(slate.filtered_out),
        )


class OfferCreate(InputModel):
    organization_id: uuid.UUID | None = Field(
        default=None, description="Any organisation in the eligible slate. Omit for the top candidate."
    )


class RejectIn(InputModel):
    reason_code: RejectReason
    note: Note | None = None


class ScheduleIn(InputModel):
    scheduled_for: AwareDatetime


class ReasonIn(InputModel):
    """Every admin action records why."""

    reason: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=NOTE_MAX_LENGTH)]
