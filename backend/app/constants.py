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

from datetime import timedelta
from decimal import Decimal
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
    """Only VERIFIED organisations enter matching."""

    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


class DonationStatus(StrEnum):
    """Donation lifecycle states. Which state may follow which is defined only in
    `app.domain.lifecycle`."""

    LISTED = "LISTED"
    MATCHED = "MATCHED"
    RE_MATCHING = "RE_MATCHING"
    ESCALATED = "ESCALATED"
    ACCEPTED = "ACCEPTED"
    PICKUP_SCHEDULED = "PICKUP_SCHEDULED"
    IN_TRANSIT = "IN_TRANSIT"
    COMPLETED = "COMPLETED"
    WASTE_REDIRECTED = "WASTE_REDIRECTED"
    RECYCLING_SCHEDULED = "RECYCLING_SCHEDULED"
    RECYCLING_IN_TRANSIT = "RECYCLING_IN_TRANSIT"
    RECYCLED = "RECYCLED"
    NEEDS_ADMIN = "NEEDS_ADMIN"
    CANCELLED = "CANCELLED"


class DonationAction(StrEnum):
    """Things that can happen to a donation. The lifecycle table maps
    (state, action) -> next state, and declares who may perform each."""

    OFFER = "OFFER"
    ESCALATE = "ESCALATE"
    CANCEL = "CANCEL"
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"
    EXPIRE = "EXPIRE"
    REOFFER = "REOFFER"
    REMATCH = "REMATCH"
    UPGRADE_PRIORITY = "UPGRADE_PRIORITY"
    REDIRECT_TO_RECYCLING = "REDIRECT_TO_RECYCLING"
    STALL = "STALL"
    SCHEDULE_PICKUP = "SCHEDULE_PICKUP"
    CHOOSE_DROPOFF = "CHOOSE_DROPOFF"
    MARK_HANDED_OVER = "MARK_HANDED_OVER"
    CONFIRM_RECEIPT = "CONFIRM_RECEIPT"
    CONFIRM_RECYCLED = "CONFIRM_RECYCLED"
    NO_RECYCLER = "NO_RECYCLER"
    REQUEUE = "REQUEUE"
    BOOK_PICKUP = "BOOK_PICKUP"
    CHOOSE_ACCEPTOR_COLLECTION = "CHOOSE_ACCEPTOR_COLLECTION"
    DELIVER_TO_RECYCLER = "DELIVER_TO_RECYCLER"
    BOOK_RECYCLER_PICKUP = "BOOK_RECYCLER_PICKUP"
    MARK_RECYCLER_HANDED_OVER = "MARK_RECYCLER_HANDED_OVER"


class Actor(StrEnum):
    """Who performs a lifecycle action. SYSTEM covers both in-request automation
    (re-offers, escalation) and the sweeper."""

    DONOR = "DONOR"
    ACCEPTOR = "ACCEPTOR"
    ADMIN = "ADMIN"
    SYSTEM = "SYSTEM"


class EscalationCause(StrEnum):
    """Why the system escalated a donation to its donor."""

    THRESHOLD_REACHED = "THRESHOLD_REACHED"  # ESCALATION_THRESHOLD declines since the last escalation
    NO_CANDIDATES = "NO_CANDIDATES"  # the eligible slate is empty
    NOT_OFFERED = "NOT_OFFERED"  # LISTED for LISTED_STALL without the donor making an offer


class OfferSource(StrEnum):
    """Whether an offer was the donor's choice or made by the system (re-offers)."""

    DONOR = "DONOR"
    SYSTEM = "SYSTEM"


class OfferResponse(StrEnum):
    """The single, write-once response to an offer (a Match row)."""

    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"  # no answer within OFFER_TTL
    # Closed for a reason that is not the acceptor's: the donor cancelled. Not a decline,
    # and not counted in the acceptance rate.
    RETRACTED = "RETRACTED"


class RejectReason(StrEnum):
    NO_CAPACITY = "NO_CAPACITY"
    NOT_NEEDED = "NOT_NEEDED"
    CONDITION = "CONDITION"
    TOO_FAR = "TOO_FAR"
    OTHER = "OTHER"


class HandoverMode(StrEnum):
    """Decides who sets the handover time, not who performs the transitions."""

    ACCEPTOR_PICKUP = "ACCEPTOR_PICKUP"  # the acceptor collects; it sets scheduled_for
    DONOR_DROPOFF = "DONOR_DROPOFF"  # the donor delivers; the donor sets scheduled_for
    PLATFORM_PICKUP = "PLATFORM_PICKUP"  # a simulated courier collects; the donor books and sets scheduled_for


class AddressAccess(StrEnum):
    """Audited disclosures of a donor's precise pickup address."""

    RELEASED_TO_ACCEPTOR = "RELEASED_TO_ACCEPTOR"
    ADMIN_VIEWED = "ADMIN_VIEWED"


class ScoreFactor(StrEnum):
    """Ranking factors. Donor rating is deliberately absent until reviews exist."""

    PROXIMITY = "PROXIMITY"
    NEED_MATCH = "NEED_MATCH"
    URGENCY = "URGENCY"
    CAPACITY_HEADROOM = "CAPACITY_HEADROOM"
    ACCEPTANCE_RATE = "ACCEPTANCE_RATE"


class FilterReason(StrEnum):
    """Why an organisation was left out of a slate (hard filters, applied before scoring)."""

    NOT_VERIFIED = "NOT_VERIFIED"
    CATEGORY_NOT_ACCEPTED = "CATEGORY_NOT_ACCEPTED"
    EXCLUDED = "EXCLUDED"  # already offered this donation
    OUT_OF_RADIUS = "OUT_OF_RADIUS"
    INSUFFICIENT_CAPACITY = "INSUFFICIENT_CAPACITY"


class RankingTrigger(StrEnum):
    """What caused a stored ranking run."""

    DONOR_OFFER = "DONOR_OFFER"
    RE_MATCHING = "RE_MATCHING"


class RedirectReason(StrEnum):
    """The recorded reason on a donation sent to recycling by its donor (the reason on
    an admin redirect is the admin's own free text)."""

    DONOR_CHOICE = "DONOR_CHOICE"


class ImpactOutcome(StrEnum):
    """Which outcome an impact record counts toward. Reuse and recovery are reported
    separately; carbon is only ever counted for reuse."""

    REUSED = "REUSED"  # COMPLETED
    RECYCLED = "RECYCLED"  # RECYCLED


class ChatClosure(StrEnum):
    """Why a donor-organisation chat thread no longer takes messages (it stays readable)."""

    # The organisation stopped holding the donation without completing it: it stalled to
    # the admin queue, was requeued, cancelled or redirected to recycling.
    NO_LONGER_HELD = "NO_LONGER_HELD"


class NotificationKind(StrEnum):
    """What an item in the in-app notification feed is about."""

    DONATION_EVENT = "DONATION_EVENT"  # a lifecycle transition (a status_events row)
    ORGANISATION_REGISTERED = "ORGANISATION_REGISTERED"  # admins: a new organisation to verify
    CHAT_MESSAGE = "CHAT_MESSAGE"  # a message from the other party in a chat thread


class BookingStatus(StrEnum):
    """A platform-arranged pickup's own progress. Derived from Booking's nullable
    write-once timestamps (app.models.logistics), never stored as a column."""

    BOOKED = "BOOKED"
    PICKED_UP = "PICKED_UP"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


class PaymentStatus(StrEnum):
    """Derived from Payment.refunded_at, never stored as a column."""

    SUCCEEDED = "SUCCEEDED"
    REFUNDED = "REFUNDED"


class WalletTxnType(StrEnum):
    """One row per ledger entry; the balance is SUM(amount), never stored."""

    RECYCLING_CREDIT = "RECYCLING_CREDIT"  # a confirmed recycling settlement
    PICKUP_DEBIT = "PICKUP_DEBIT"  # wallet credit applied to a platform pickup booking
    PICKUP_REFUND = "PICKUP_REFUND"  # a cancelled, undelivered booking's wallet portion returned


class CommissionSource(StrEnum):
    """What earned a commission ledger entry. A cancelled booking's commission is
    reversed by a second, negative entry (never edited or deleted)."""

    LOGISTICS = "LOGISTICS"
    RECYCLING = "RECYCLING"


# --- Units ---------------------------------------------------------------------------
# Donation.quantity, OrganizationProfile.storage_capacity and CurrentNeed.quantity_needed
# are all COUNTS OF ITEMS (e.g. 12 shirts), never kilograms or bags. Mass is estimated
# from counts (CATEGORY_WEIGHT_KG below), and labelled as an estimate wherever it appears.

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
CHAT_MESSAGE_MAX_LENGTH = 2_000
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

# --- Matching: hard filters and score -----------------------------------------------
# Weights are ASSIGNED, not learned: at launch there is no accept/reject history to learn
# from. Every ranking run stores its full slate and config_version so they can be
# calibrated later (Phase 5). Each factor is in [0, 1]; the weights sum to 1.
# Donor rating is left out until reviews exist.

SCORE_WEIGHTS = {
    ScoreFactor.PROXIMITY: 0.30,
    ScoreFactor.NEED_MATCH: 0.25,
    ScoreFactor.URGENCY: 0.15,
    ScoreFactor.CAPACITY_HEADROOM: 0.15,
    ScoreFactor.ACCEPTANCE_RATE: 0.15,
}
# Urgency of the organisation's active need in the donation's category; 0 with no need.
URGENCY_FACTOR = {Urgency.LOW: 0.33, Urgency.MEDIUM: 0.67, Urgency.HIGH: 1.0}
# Acceptance rate is smoothed toward a neutral prior, so a new organisation scores the
# prior rather than 0 or 1: (accepted + W * P) / (decided + W).
ACCEPTANCE_PRIOR_RATE = 0.5
ACCEPTANCE_PRIOR_WEIGHT = 4

MAX_RADIUS_KM = 15.0  # search radius with no declines

# --- Rejection boost and priority -----------------------------------------------------
# A multiplier on one donation's candidate scores would not change their order, so the
# boosts never touch scores. They act on:
#   reach:          radius = MAX_RADIUS_KM * (1 + RADIUS_STEP * declines), capped
#   queue priority: an acceptor's inbox is ordered by
#                   (PRIORITY_BOOST if flagged else 1) * (1 + REJECTION_BOOST_STEP * declines, capped)
# "Declines" are REJECTED and EXPIRED offers. Both rejection effects switch off with the
# flag below, so their effect can be measured against the plain score.

REJECTION_BOOST_ENABLED = True
REJECTION_BOOST_STEP = 0.2
REJECTION_BOOST_CAP = 2.0
RADIUS_STEP = 0.25
RADIUS_CAP_KM = 30.0
PRIORITY_BOOST = 1.5

# --- Lifecycle timing -----------------------------------------------------------------

# The donor's pickup window is advisory: shown to acceptors, never a deadline.

ESCALATION_THRESHOLD = 3  # declines since the last escalation
LISTED_STALL = timedelta(days=7)  # a LISTED donation never offered then ESCALATEs (NOT_OFFERED)
OFFER_TTL = timedelta(hours=48)  # an unanswered offer then EXPIREs (a decline)
ESCALATION_TTL = timedelta(hours=72)  # a silent donor's donation then STALLs to NEEDS_ADMIN
# Time allowed in a state before the sweeper STALLs the donation to NEEDS_ADMIN, measured
# from entering the state. PICKUP_SCHEDULED is measured from the agreed handover time.
STALL_TIMEOUTS = {
    DonationStatus.ACCEPTED: timedelta(hours=72),
    DonationStatus.IN_TRANSIT: timedelta(hours=48),
    DonationStatus.WASTE_REDIRECTED: timedelta(days=7),
    DonationStatus.RECYCLING_SCHEDULED: timedelta(hours=72),  # same as ACCEPTED: booked, not yet handed over
    DonationStatus.RECYCLING_IN_TRANSIT: timedelta(hours=48),  # same as IN_TRANSIT
}
HANDOVER_GRACE = timedelta(hours=48)  # after scheduled_for, before PICKUP_SCHEDULED stalls
# How often the in-process sweeper runs (app.main lifespan; off when SWEEPER_ENABLED=false).
SWEEP_INTERVAL = timedelta(minutes=15)

# --- Address privacy ------------------------------------------------------------------

# Before acceptance an acceptor sees only distance, rounded to this step.
DISTANCE_DISCLOSURE_STEP_KM = 0.5
# The public discovery map shows verified organisations at positions rounded to this many
# decimal places of a degree (2: within about 0.8 km), and never their address.
DISCOVERY_COORD_DECIMALS = 2

# --- Recycling (simulated settlement) -------------------------------------------------

# PLACEHOLDER VALUES, pending a cited source. Estimated mass per item, in kg. Settlement
# mass = quantity * weight. Every API response that uses them says they are placeholders.
CATEGORY_WEIGHT_KG = {
    Category.CLOTHES: Decimal("0.5"),
    Category.TOYS: Decimal("0.3"),
    Category.BOOKS: Decimal("0.4"),
}
CATEGORY_WEIGHTS_ARE_PLACEHOLDERS = True
RECYCLER_MAX_RADIUS_KM = 25.0
RECYCLING_PLATFORM_FEE_PCT = Decimal("10")  # of the gross recovered value
CURRENCY = "INR"

# --- Impact (estimated) ---------------------------------------------------------------
# PLACEHOLDER VALUES, NOT SOURCED. Estimated carbon avoided per item by reuse (kg CO2e),
# the figure a reused donation is credited with. Replace with a cited source before any
# figure is quoted externally. Shown in every impact response under the same
# CATEGORY_WEIGHTS_ARE_PLACEHOLDERS flag, which covers every unsourced impact factor.
# Recycling is credited with mass only: no carbon figure is defined for it.
CARBON_FACTOR_KG_PER_ITEM = {
    Category.CLOTHES: Decimal("5.0"),
    Category.TOYS: Decimal("2.0"),
    Category.BOOKS: Decimal("1.5"),
}

# --- Logistics (simulated platform-arranged pickup) ------------------------------------
# A LogisticsProvider's own pricing (base fee + per-km rate) lives on its record, not
# here, same as a WasteCollector's rate. This fee is an independent policy choice from
# RECYCLING_PLATFORM_FEE_PCT, even though both currently start at the same value.

LOGISTICS_PLATFORM_FEE_PCT = Decimal("10")  # of the booking cost the donor pays
