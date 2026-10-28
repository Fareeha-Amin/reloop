"""Operator commands.

    python -m app.cli create-admin --email admin@example.org --name "Platform Admin"
    python -m app.cli seed
    python -m app.cli sweep
    python -m app.cli export-openapi
    python -m app.cli train-model [--include-synthetic]
    python -m app.cli show-model
    python -m app.cli purge-synthetic [--tag NAME]
    python -m app.cli copy-dev-to-test

Admins cannot self-register; create-admin is the only way to create one. Passwords are
prompted for (twice) and never passed on the command line, where they would end up in
shell history.

`sweep` applies every due deadline once and exits, so Windows Task Scheduler (or cron)
can run it on a schedule. It always uses the real clock.

`export-openapi` writes the API schema the frontend generates its types from. A test
fails if the committed copy is out of date.
"""

import argparse
import getpass
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.config import get_settings

from app.db import get_engine
from app.models import User
from app.schemas.user import AdminCreate
from app.services import seed as seed_service
from app.constants import ScoreFactor
from app.domain import learning
from app.services import dev_copy, sweeper, training, users
from app.services.errors import ServiceError


def create_admin(db: Session, email: str, password: str, name: str) -> User:
    """Validates with the same rules as registration, then creates the admin."""
    data = AdminCreate(email=email, password=password, full_name=name)
    return users.create_admin(
        db, email=data.email, password=data.password, full_name=data.full_name
    )


def _prompt_password(prompt: str = "Password: ") -> str | None:
    password = getpass.getpass(prompt)
    if getpass.getpass("Repeat password: ") != password:
        print("Passwords do not match.", file=sys.stderr)
        return None
    return password


def _create_admin(args) -> int:
    password = _prompt_password()
    if password is None:
        return 1
    try:
        with Session(get_engine()) as db:
            user = create_admin(db, args.email, password, args.name)
            email = user.email
    except ValidationError as exc:
        print(f"Invalid input:\n{exc}", file=sys.stderr)
        return 1
    except ServiceError as exc:
        print(exc.detail, file=sys.stderr)
        return 1
    print(f"Created admin {email}")
    return 0


def _seed(args) -> int:
    print(f"Seed accounts ({len(seed_service.ORGANISATIONS)} organisations and the demo donor) share one password.")
    password = _prompt_password("Password for seed accounts: ")
    if password is None:
        return 1
    try:
        with Session(get_engine()) as db:
            report = seed_service.seed(db, password)
    except ValidationError as exc:
        print(f"Invalid input:\n{exc}", file=sys.stderr)
        return 1
    print(f"Organisations created: {len(report.organisations_created)}, already present: {len(report.organisations_existing)}")
    print(f"Recyclers created: {len(report.recyclers_created)}, already present: {len(report.recyclers_existing)}")
    print(f"Logistics providers created: {len(report.providers_created)}, already present: {len(report.providers_existing)}")
    print(f"Demo donor {seed_service.DEMO_DONOR_EMAIL}: {'created' if report.donor_created else 'already present'}")
    print(f"Organisation logins: seed.<slug>@{seed_service.SEED_EMAIL_DOMAIN}, e.g. {seed_service.ORGANISATIONS[0].email}")
    print("Existing accounts keep their original password.")
    return 0


def _sweep(args) -> int:
    with Session(get_engine()) as db:
        report = sweeper.sweep(db, datetime.now(UTC))
    print(f"Swept at {report.now.isoformat()}: examined {report.examined}, applied {len(report.applied)}, "
          f"skipped (locked) {report.skipped_locked}, errors {len(report.errors)}")
    for item in report.applied:
        print(f"  {item.donation_id}  {item.from_state} --{item.action}--> {item.to_state}")
    for error in report.errors:
        print(f"  ERROR {error}", file=sys.stderr)
    return 1 if report.errors else 0


def _train_model(args) -> int:
    with Session(get_engine()) as db:
        report = training.train(db, include_synthetic=args.include_synthetic)
        active = training.active_model(db)
    real = report.real
    print(f"Real outcomes: {real.total} labelled ({real.accepted} accepted, {real.declined} declined).")
    synthetic = report.synthetic_available
    print(f"Synthetic outcomes available: {synthetic.total} ({synthetic.accepted} accepted); "
          f"used: {'yes, sandbox only' if report.include_synthetic else 'no'}.")
    row = report.version
    if report.activated:
        print(f"Gate: MET. Fit activated: {row.config_version}.")
    else:
        print("Gate: NOT MET. No weights were activated.")
        for reason in report.reasons:
            print(f"  - {reason}")
    if active is None:
        print("Active weights: the cold-start prior (SCORE_WEIGHTS).")
    else:
        print(f"Active weights: fit {active.config_version} (seq {active.seq}).")
    print(f"Audit row: model_versions seq {row.seq}, activated={str(row.activated).lower()}, "
          f"fitted={str(report.fitted).lower()}.")
    if report.fitted:
        print_fit(row)
    return 0


def print_fit(version) -> None:
    fit = version.fit
    if fit is None:
        return
    print(f"Split: {fit['train_n']} training, {fit['holdout_n']} held out (by donation).")
    print(f"Held-out log-loss: fitted {fit['fitted_holdout_loss']}, prior {fit['prior_holdout_loss']}.")
    print(f"Held-out AUC: fitted {fit['fitted_holdout_auc']}, prior {fit['prior_holdout_auc']}.")
    print(f"Largest weight shift from the prior: {fit['max_shift_from_prior']}")
    print(f"{'factor':<20}{'prior':>8}{'fitted':>10}{'90% interval':>22}{'unconstrained (logit)':>24}")
    for f in ScoreFactor:
        prior = fit["prior_weights"][f.value]
        fitted = version.weights[f.value]
        interval = fit["intervals"][f.value]
        interval_text = f"[{interval[0]:.3f}, {interval[1]:.3f}]" if interval else "n/a"
        unconstrained = fit["unconstrained_coefficients"]
        raw = f"{unconstrained[f.value]:.3f}" if unconstrained else "n/a"
        print(f"{f.value:<20}{prior:>8.3f}{fitted:>10.3f}{interval_text:>22}{raw:>24}")


def _show_model(args) -> int:
    with Session(get_engine()) as db:
        row = training.active_model(db)
        config = training.active_config(db)
        attempt = training.latest_attempt(db)
    if row is None:
        print(f"Active weights: the cold-start prior (SCORE_WEIGHTS), version {config.version()}.")
        print("No fit has been activated.")
    else:
        print(f"Active weights: fit {row.config_version} (seq {row.seq}), recorded {row.created_at.isoformat()}.")
        if row.sandbox:
            print("DEMO FIT: trained on simulated data only (test database). Not real behaviour.")
        print(f"Trained on {row.real_n} real ({row.real_accepted} accepted) and {row.synthetic_n} synthetic "
              f"({row.synthetic_accepted} accepted) outcomes.")
        print_fit(row)
    if attempt is None:
        print("Latest training attempt: none.")
    else:
        print(f"Latest training attempt: seq {attempt.seq}, activated={str(attempt.activated).lower()}, "
              f"real {attempt.real_n} ({attempt.real_accepted} accepted).")
        for reason in attempt.reasons:
            print(f"  - {reason}")
    return 0


def _purge_synthetic(args) -> int:
    with Session(get_engine()) as db:
        removed = training.purge_synthetic(db, args.tag)
    scope = f"tag {args.tag!r}" if args.tag else "every tag"
    print(f"Removed {removed} synthetic outcomes ({scope}). Real outcomes are untouched.")
    return 0


def _copy_dev_to_test(args) -> int:
    settings = get_settings()
    if not settings.test_database_url:
        print("TEST_DATABASE_URL is not set.", file=sys.stderr)
        return 1
    target = create_engine(settings.test_database_url)
    try:
        report = dev_copy.copy_rows(get_engine(), target)
    except dev_copy.CopyRefused as exc:
        print(f"Refused: {exc}", file=sys.stderr)
        return 1
    finally:
        target.dispose()
    print(f"Copied from {make_url(settings.database_url).database} (read-only) "
          f"into {make_url(settings.test_database_url).database}:")
    print(f"  {'table':<24}{'source':>8}{'copied':>8}")
    for name, (source_rows, copied) in report.items():
        print(f"  {name:<24}{source_rows:>8}{copied:>8}")
    print(f"Not copied: {', '.join(sorted(dev_copy.EXCLUDED))}. Uploaded images are shared files, not rows.")
    return 0


FRONTEND_OPENAPI = Path(__file__).resolve().parents[2] / "frontend" / "src" / "api" / "openapi.json"


def openapi_json() -> str:
    """The OpenAPI document, as committed for the frontend (stable formatting)."""
    from app.main import app

    return json.dumps(app.openapi(), indent=2, ensure_ascii=False) + "\n"


def _export_openapi(args) -> int:
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(openapi_json(), encoding="utf-8", newline="\n")
    print(f"Wrote {out}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    admin = sub.add_parser("create-admin", help="Create an admin account.")
    admin.add_argument("--email", required=True)
    admin.add_argument("--name", default="Platform Admin")
    admin.set_defaults(handler=_create_admin)
    sub.add_parser("seed", help="Add Bengaluru seed organisations, recyclers and a demo donor (idempotent).").set_defaults(handler=_seed)
    sub.add_parser("sweep", help="Apply every due deadline once (for a scheduler).").set_defaults(handler=_sweep)
    export = sub.add_parser("export-openapi", help="Write the OpenAPI schema for the frontend's generated types.")
    export.add_argument("--out", default=str(FRONTEND_OPENAPI))
    export.set_defaults(handler=_export_openapi)
    train = sub.add_parser("train-model", help="Fit the ranking weights from real outcomes; activate if the gate passes.")
    train.add_argument("--include-synthetic", action="store_true", help="Sandbox fit with synthetic data. Never activated.")
    train.set_defaults(handler=_train_model)
    sub.add_parser("show-model", help="Show the active weights against the prior.").set_defaults(handler=_show_model)
    purge = sub.add_parser("purge-synthetic", help="Delete synthetic outcomes (never real ones).")
    purge.add_argument("--tag", default=None, help="Only this run's outcomes. Omit for all synthetic outcomes.")
    purge.set_defaults(handler=_purge_synthetic)
    sub.add_parser(
        "copy-dev-to-test",
        help="Copy dev rows into the EMPTY test database for demos. Dev is only read.",
    ).set_defaults(handler=_copy_dev_to_test)
    args = parser.parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    sys.exit(main())
