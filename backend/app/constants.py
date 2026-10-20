"""The single source of truth for every domain vocabulary and tunable value.

Non-negotiables 4 and 9: each value below is defined here once and imported everywhere.
`tests/unit/test_constants.py` fails if any vocabulary value is written as a string
literal anywhere else in `app/`.

Vocabularies are stored as VARCHAR columns (no native Postgres ENUM types) and validated
in code: by the Pydantic schemas at the API edge, and by `app.db.StrEnumType` at the
model edge. There are deliberately no CHECK constraints repeating these values in the
database — that would be a second copy. Writes made outside the application are not
validated; that trade-off is accepted (see CLAUDE.md, Decisions).

Environment-specific values (connection strings, secrets) live in `app.config`, not here.
"""

from enum import StrEnum
from pathlib import Path


# --- Vocabularies -------------------------------------------------------------------


class Role(StrEnum):
    DONOR = "DONOR"
    ACCEPTOR = "ACCEPTOR"
    ADMIN = "ADMIN"


class Category(StrEnum):
    """MVP categories. Food is deliberately out of scope (no cold-chain handling)."""

    CLOTHES = "CLOTHES"
    TOYS = "TOYS"
    BOOKS = "BOOKS"


class Condition(StrEnum):
    NEW = "NEW"
    GENTLY_USED = "GENTLY_USED"
    USED = "USED"


class Urgency(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class VerificationStatus(StrEnum):
    """Only VERIFIED organisations will enter matching (Phase 2)."""

    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


class DonationStatus(StrEnum):
    """Donation lifecycle states. Which state may follow which is defined only in
    `app.domain.lifecycle`. Phase 1 has LISTED and CANCELLED; the matching states and
    the outcome states COMPLETED and RECYCLED arrive in Phase 2."""

    LISTED = "LISTED"
    CANCELLED = "CANCELLED"


class DonationAction(StrEnum):
    """Things that can happen to a donation. The lifecycle table maps
    (state, action) -> next state."""

    CANCEL = "CANCEL"


# --- Units ---------------------------------------------------------------------------
# Donation.quantity, OrganizationProfile.storage_capacity and CurrentNeed.quantity_needed
# are all COUNTS OF ITEMS (e.g. 12 shirts), never kilograms or bags. Mass is estimated
# from counts later (Phase 2+), and labelled as an estimate when it is.

QUANTITY_MAX = 1_000  # upper bound on a single donation or need, in items
STORAGE_CAPACITY_MAX = 1_000_000  # items

# --- Auth ----------------------------------------------------------------------------

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_TTL_MINUTES = 30
REFRESH_TOKEN_TTL_DAYS = 7
PASSWORD_MIN_LENGTH = 10
PASSWORD_MAX_LENGTH = 128  # Argon2 has no length limit; this bounds hashing cost per request

# --- Text fields ----------------------------------------------------------------------

NAME_MAX_LENGTH = 200
ADDRESS_MAX_LENGTH = 300
NOTE_MAX_LENGTH = 1_000
REGISTRATION_ID_MAX_LENGTH = 64
PHONE_PATTERN = r"^\+?[0-9][0-9 ()-]{6,19}$"

# --- Image uploads --------------------------------------------------------------------

IMAGE_MAX_BYTES = 5 * 1024 * 1024  # per file, as uploaded
IMAGE_MAX_PIXELS = 40_000_000  # anything larger is treated as a decompression bomb
IMAGES_PER_DONATION_MAX = 6
# Pillow format name -> (served content type, stored file extension)
IMAGE_FORMATS = {
    "JPEG": ("image/jpeg", "jpg"),
    "PNG": ("image/png", "png"),
    "WEBP": ("image/webp", "webp"),
}
JPEG_QUALITY = 90
WEBP_QUALITY = 90
# Local image storage root. Replaced by object storage later (see app/services/storage.py).
UPLOAD_DIR = Path(__file__).resolve().parents[1] / "uploads"

# --- Pagination -----------------------------------------------------------------------

PAGE_SIZE_DEFAULT = 20
PAGE_SIZE_MAX = 100
