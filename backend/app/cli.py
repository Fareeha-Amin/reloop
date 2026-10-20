"""Operator commands. Admins cannot self-register; this is the only way to create one.

    python -m app.cli create-admin --email admin@example.org --name "Platform Admin"

The password is prompted for (twice) and never passed on the command line, where it
would end up in shell history.
"""

import argparse
import getpass
import sys

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.db import get_engine
from app.models import User
from app.schemas.user import AdminCreate
from app.services import users
from app.services.errors import ServiceError


def create_admin(db: Session, email: str, password: str, name: str) -> User:
    """Validates with the same rules as registration, then creates the admin."""
    data = AdminCreate(email=email, password=password, full_name=name)
    return users.create_admin(
        db, email=data.email, password=data.password, full_name=data.full_name
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    admin = sub.add_parser("create-admin", help="Create an admin account.")
    admin.add_argument("--email", required=True)
    admin.add_argument("--name", default="Platform Admin")
    args = parser.parse_args(argv)

    password = getpass.getpass("Password: ")
    if getpass.getpass("Repeat password: ") != password:
        print("Passwords do not match.", file=sys.stderr)
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


if __name__ == "__main__":
    sys.exit(main())
