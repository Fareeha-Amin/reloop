"""Generate synthetic outcomes and store them apart from real history.

    python -m sim generate --tag NAME [--seed N] [--orgs N] [--donations N]
    python -m sim demo [--tag NAME] [--seed N] [--orgs N] [--donations N] [--offer-pool N]

`generate` writes to DATABASE_URL (additive only). Remove them with
`python -m app.cli purge-synthetic`.

`demo` is for demonstrations. It connects to TEST_DATABASE_URL and nowhere else (it never
touches DATABASE_URL's database), generates synthetic outcomes, fits on them alone and
ACTIVATES the fit if it beats the prior on held-out donations. The activated fit is
labelled a demo fit trained on simulated data in every breakdown. It is an exception to
"synthetic data never activates", which still holds for `python -m app.cli train-model`.
"""

import argparse
import sys

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.cli import print_fit
from app.config import get_settings
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


def _same_database(a: str, b: str) -> bool:
    ua, ub = make_url(a), make_url(b)
    return (ua.host, ua.port or 5432, ua.database) == (ub.host, ub.port or 5432, ub.database)


def _demo(args) -> int:
    settings = get_settings()
    if not settings.test_database_url:
        print("TEST_DATABASE_URL is not set. The demo runs on the test database only.", file=sys.stderr)
        return 1
    if _same_database(settings.test_database_url, settings.database_url):
        print(
            "Refusing: TEST_DATABASE_URL and DATABASE_URL name the same database. Run the demo in a shell "
            "where DATABASE_URL is not pointed at the test database.",
            file=sys.stderr,
        )
        return 1

    generated = world.generate(args.seed, orgs=args.orgs, donations=args.donations)
    offers = engine.run(generated, args.seed, offer_pool=args.offer_pool)
    test_engine = create_engine(settings.test_database_url)
    try:
        with Session(test_engine) as db:
            training.assert_test_database(db)
            training.purge_synthetic(db, args.tag)  # only this tag, so the demo can be re-run
            training.record_synthetic(db, args.tag, args.seed, offers)
            report = training.demo_fit(db)
            active = training.active_model(db)
            accepted = sum(1 for o in offers if o.accepted)
            print(f"Database: {make_url(settings.test_database_url).database} (test database only).")
            print(f"Synthetic outcomes: {len(offers)} ({accepted} accepted, {len(offers) - accepted} declined) "
                  f"from {args.donations} donations and {args.orgs} organisations, seed {args.seed}, "
                  f"donor chooses among the top {args.offer_pool} candidates.")
            print(f"Real outcomes counted but not fitted: {report.real.total}.")
            if report.activated:
                print(f"Gate (held-out log-loss beats the prior): MET. Demo fit activated: {report.version.config_version}.")
            else:
                print("Gate: NOT MET. Nothing was activated; the prior stays active.")
                for reason in report.reasons:
                    print(f"  - {reason}")
            print(f"Audit row: model_versions seq {report.version.seq}, activated={str(report.version.activated).lower()}, "
                  "sandbox=true (trained on simulated data).")
            if report.fitted:
                print_fit(report.version)
            print("Active weights: " + ("the cold-start prior." if active is None else f"demo fit {active.config_version}."))
            print("This is a DEMO FIT trained on simulated data. It shows the pipeline and the weights it produces from "
                  "rules we wrote; it says nothing about real organisations.")
    except training.DemoNotAllowed as exc:
        print(str(exc), file=sys.stderr)
        return 1
    finally:
        test_engine.dispose()
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
    demo = sub.add_parser("demo", help="Test database only: generate, fit on synthetic data and activate the fit.")
    demo.add_argument("--tag", default="college-demo")
    demo.add_argument("--seed", type=int, default=1)
    demo.add_argument("--orgs", type=int, default=60)
    demo.add_argument("--donations", type=int, default=3000)
    demo.add_argument("--offer-pool", type=int, default=8, help="Top candidates a simulated donor chooses among.")
    demo.set_defaults(handler=_demo)
    args = parser.parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    sys.exit(main())
