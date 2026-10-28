"""The simulation's hidden acceptance model. An assumption, labelled as one.

It is deliberately not SCORE_WEIGHTS, so a training run on synthetic data has something
to recover. The numbers are invented: they describe the generator, not real acceptors.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from app.constants import ScoreFactor


@dataclass(frozen=True)
class TrueModel:
    intercept: float
    coefficients: Mapping[ScoreFactor, float]


TRUE_MODEL = TrueModel(
    intercept=-6.5,
    coefficients=MappingProxyType(
        {
            ScoreFactor.PROXIMITY: 4.0,
            ScoreFactor.NEED_MATCH: 2.0,
            ScoreFactor.URGENCY: 0.5,
            ScoreFactor.CAPACITY_HEADROOM: 0.5,
            ScoreFactor.ACCEPTANCE_RATE: 1.0,
        }
    ),
)
