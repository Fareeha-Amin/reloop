from pydantic import Field

from app.constants import CATEGORY_WEIGHTS_ARE_PLACEHOLDERS
from app.domain.impact import Totals
from app.schemas.common import OutputModel


class ImpactTotalsOut(OutputModel):
    """Totals over finished donations. Every figure is an ESTIMATE: mass is modelled from
    item counts, and carbon from a per-item factor. Reuse and recycling are separate.
    `placeholders` is true while the per-item factors are unsourced."""

    estimated: bool = True
    placeholders: bool
    reused_donations: int
    reused_items: int
    reused_mass_kg: float
    recycled_donations: int
    recycled_items: int
    recycled_mass_kg: float
    carbon_avoided_kg: float = Field(description="Reuse only; recycling is never credited with carbon.")

    @classmethod
    def build(cls, t: Totals) -> "ImpactTotalsOut":
        return cls(
            placeholders=CATEGORY_WEIGHTS_ARE_PLACEHOLDERS,
            reused_donations=t.reused_donations,
            reused_items=t.reused_items,
            reused_mass_kg=float(t.reused_mass_kg),
            recycled_donations=t.recycled_donations,
            recycled_items=t.recycled_items,
            recycled_mass_kg=float(t.recycled_mass_kg),
            carbon_avoided_kg=float(t.carbon_avoided_kg),
        )
