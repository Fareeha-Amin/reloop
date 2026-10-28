"""Ranking slates and the inputs to lifecycle actions."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Annotated

from pydantic import AwareDatetime, Field, StringConstraints

from app.constants import NOTE_MAX_LENGTH, FilterReason, RejectReason, ScoreFactor
from app.domain.scoring import Candidate, Slate
from app.schemas.common import InputModel, Note, OutputModel

if TYPE_CHECKING:
    from app.services.training import ModelView


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


class TrainingSampleOut(OutputModel):
    """What a fitted set of weights was trained on, split by source."""

    real: int = Field(description="Labelled real offers (ACCEPTED, REJECTED, EXPIRED). Zero for the prior.")
    real_accepted: int
    synthetic: int = Field(
        description="Simulated offers used. Zero for any fit made from real outcomes; non-zero only for a synthetic demo fit."
    )
    synthetic_accepted: int


class ModelOut(OutputModel):
    """The weights behind a breakdown: the cold-start prior, or a fit from real outcomes."""

    config_version: str = Field(description="Fingerprint of the full matching configuration the weights belong to.")
    is_prior: bool = Field(description="True: the cold-start prior (the assigned SCORE_WEIGHTS), not a fit.")
    trained_at: datetime | None = Field(description="When the activated fit was recorded; null for the prior.")
    training_sample: TrainingSampleOut
    is_synthetic_demo: bool = Field(
        description="True: the weights were fitted on simulated data for a demonstration on the test database, not on real outcomes."
    )
    max_shift_from_prior: float | None = Field(
        description="Largest change in any factor's weight from the prior, as a share of the score (0 to 1). Null for the prior."
    )

    @classmethod
    def from_view(cls, view: "ModelView") -> "ModelOut":
        return cls(
            config_version=view.config_version,
            is_prior=view.is_prior,
            trained_at=view.trained_at,
            training_sample=TrainingSampleOut(
                real=view.real.total,
                real_accepted=view.real.accepted,
                synthetic=view.synthetic.total,
                synthetic_accepted=view.synthetic.accepted,
            ),
            is_synthetic_demo=view.is_synthetic_demo,
            max_shift_from_prior=view.max_shift_from_prior,
        )


class SlateOut(OutputModel):
    """The donation's eligible organisations, best first. A preview: nothing is stored
    until an offer is made, which re-ranks and stores the slate it was made against."""

    radius_km: float = Field(description="Search radius; widens with each decline (capped).")
    declines: int
    config_version: str
    model: ModelOut
    candidates: list[CandidateOut]
    filtered_out: dict[FilterReason, int] = Field(
        description="Organisations accepting this category that the hard filters removed, by reason."
    )

    @classmethod
    def from_slate(cls, slate: Slate, declines: int, model: ModelOut) -> "SlateOut":
        return cls(
            radius_km=slate.radius_km,
            declines=declines,
            config_version=model.config_version,
            model=model,
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
