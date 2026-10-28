"""Synthetic organisations and donations, placed in Bengaluru's bounding box."""

import random
import uuid
from dataclasses import dataclass, field

from app.constants import Category, Urgency
from app.domain.scoring import DonationFacts

# A box around central Bengaluru (south to north, west to east).
LAT_RANGE = (12.85, 13.10)
LON_RANGE = (77.45, 77.75)


@dataclass
class SimOrg:
    """A synthetic organisation. Its acceptance history grows as the run goes on."""

    id: uuid.UUID
    name: str
    latitude: float
    longitude: float
    categories: frozenset[Category]
    pickup_capable: bool
    storage_capacity: int
    needs: dict[Category, tuple[Urgency, int]]  # active needs, by category
    accepted: int = 0
    decided: int = 0


@dataclass(frozen=True)
class World:
    orgs: tuple[SimOrg, ...]
    donations: tuple[tuple[uuid.UUID, DonationFacts], ...] = field(default=())


def _uuid(rng: random.Random) -> uuid.UUID:
    return uuid.UUID(int=rng.getrandbits(128), version=4)


def generate(seed: int, *, orgs: int = 40, donations: int = 2000) -> World:
    rng = random.Random(seed)
    made_orgs = []
    for i in range(orgs):
        categories = frozenset(c for c in Category if rng.random() < 0.7) or frozenset({Category.CLOTHES})
        # Iterate in the enum's fixed order, not the frozenset's: set order depends on the
        # per-process string hash seed, which would change the random draws between runs.
        needs = {
            c: (rng.choice(list(Urgency)), rng.randint(5, 50))
            for c in Category
            if c in categories and rng.random() < 0.5
        }
        made_orgs.append(
            SimOrg(
                id=_uuid(rng),
                name=f"Simulated organisation {i + 1}",
                latitude=rng.uniform(*LAT_RANGE),
                longitude=rng.uniform(*LON_RANGE),
                categories=categories,
                pickup_capable=rng.random() < 0.5,
                storage_capacity=rng.randint(20, 300),
                needs=needs,
            )
        )
    made_donations = []
    for _ in range(donations):
        made_donations.append(
            (
                _uuid(rng),
                DonationFacts(
                    category=rng.choice(list(Category)),
                    quantity=rng.randint(1, 30),
                    latitude=rng.uniform(*LAT_RANGE),
                    longitude=rng.uniform(*LON_RANGE),
                ),
            )
        )
    return World(orgs=tuple(made_orgs), donations=tuple(made_donations))
