"""Non-negotiable 4: one source of truth for every constant.

Every vocabulary value in app.constants may appear as a string literal only in
app/constants.py. Anywhere else in app/ it must be referenced through the enum, so
changing or renaming a value can never leave a stale copy behind. (Migrations are frozen
snapshots and are deliberately not scanned.)
"""

import ast
from enum import StrEnum
from pathlib import Path

import app.constants as constants

APP_DIR = Path(constants.__file__).resolve().parent
CONSTANTS_FILE = Path(constants.__file__).resolve()

VOCABULARIES = [
    obj
    for obj in vars(constants).values()
    if isinstance(obj, type) and issubclass(obj, StrEnum) and obj is not StrEnum
]
VOCABULARY_VALUES = {member.value for enum in VOCABULARIES for member in enum}


def test_vocabularies_found():
    names = {enum.__name__ for enum in VOCABULARIES}
    assert {
        "Role",
        "Category",
        "Condition",
        "Urgency",
        "VerificationStatus",
        "DonationStatus",
        "DonationAction",
        "Actor",
        "EscalationCause",
        "OfferSource",
        "OfferResponse",
        "RejectReason",
        "HandoverMode",
        "AddressAccess",
        "ScoreFactor",
        "FilterReason",
        "RankingTrigger",
    } <= names


def test_app_code_issues_no_bulk_update_or_delete():
    """Bulk UPDATE/DELETE statements bypass the ORM, and with it the append-only guard
    (app.db.AppendOnly). App code changes rows only through the ORM."""
    offenders = []
    for path in APP_DIR.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("sqlalchemy"):
                for alias in node.names:
                    if alias.name in {"update", "delete"}:
                        offenders.append(f"{path.relative_to(APP_DIR)}:{node.lineno} {alias.name}")
    assert not offenders, "Bulk statements bypass the append-only guard:\n" + "\n".join(offenders)


def test_vocabulary_values_are_upper_snake_and_match_names():
    for enum in VOCABULARIES:
        for member in enum:
            assert member.value == member.name, f"{enum.__name__}.{member.name}"


def test_no_vocabulary_value_is_duplicated_as_a_literal_in_app_code():
    offenders = []
    for path in APP_DIR.rglob("*.py"):
        if path.resolve() == CONSTANTS_FILE:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and node.value in VOCABULARY_VALUES:
                offenders.append(f"{path.relative_to(APP_DIR)}:{node.lineno} {node.value!r}")
    assert not offenders, "Use the enum from app.constants instead of:\n" + "\n".join(offenders)


def test_only_constants_and_config_define_tunables():
    """Spot-check the tunables most likely to be copied: none of these numbers should be
    re-declared as a module-level constant elsewhere in app/."""
    tunable_names = {
        name for name, value in vars(constants).items() if name.isupper() and not name.startswith("_")
    }
    offenders = []
    for path in APP_DIR.rglob("*.py"):
        if path.resolve() == CONSTANTS_FILE:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id in tunable_names:
                        offenders.append(f"{path.relative_to(APP_DIR)}:{node.lineno} {target.id}")
    assert not offenders, "Re-declared constants:\n" + "\n".join(offenders)
