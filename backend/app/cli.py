"""Operator commands.

    python -m app.cli create-admin --email admin@example.org --name "Platform Admin"
    python -m app.cli seed
    python -m app.cli sweep
    python -m app.cli export-openapi

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
from sqlalchemy.orm import Session

from app.db import get_engine
from app.models import User
from app.schemas.user import AdminCreate
from app.services import seed as seed_service
from app.services import sweeper, users
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
    print("Seed accounts (10 organisations and the demo donor) share one password.")
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
    args = parser.parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    sys.exit(main())
