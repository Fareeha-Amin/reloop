"""Generate synthetic outcomes and store them apart from real history.

    python -m sim generate --tag NAME [--seed N] [--orgs N] [--donations N]

Writes to DATABASE_URL (additive only). Remove them with `python -m app.cli purge-synthetic`.
"""

import argparse
import sys

from sqlalchemy.orm import Session

from app.db import get_engine
from app.services import training
from sim import engine, world


def _generate(args) -> int:
    generated = world.generate(args.seed, orgs=args.orgs, donations=args.donations)
    offers = engine.run(generated, args.seed)
    with Session(get_engine()) as db:
        stored = training.record_synthetic(db, args.tag, args.seed, offers)
    accepted = sum(1 for o in offers if o.accepted)
    print(
        f"Stored {stored} synthetic offers under tag {args.tag!r} "
        f"({accepted} accepted, {stored - accepted} declined) from {args.donations} donations "
        f"and {args.orgs} organisations, seed {args.seed}."
    )
    print("These are simulated outcomes from an assumed acceptance model, not real history.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m sim")
    sub = parser.add_subparsers(dest="command", required=True)
    gen = sub.add_parser("generate", help="Generate synthetic offer outcomes and store them.")
    gen.add_argument("--tag", required=True, help="Run tag, for purging this run later.")
    gen.add_argument("--seed", type=int, default=0)
    gen.add_argument("--orgs", type=int, default=40)
    gen.add_argument("--donations", type=int, default=2000)
    gen.set_defaults(handler=_generate)
    args = parser.parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    sys.exit(main())
