"""ORM models. Tables arrive with the code that first uses them."""

from app.models.chat import ChatMessage, ChatRead
from app.models.donation import Donation, DonationImage
from app.models.events import AddressAccessEvent, StatusEvent
from app.models.impact import ImpactRecord
from app.models.logistics import Booking, LogisticsProvider, Payment
from app.models.matching import Handover, Match, RankingRun
from app.models.organization import CurrentNeed, OrganizationProfile
from app.models.recycling import Recycling, WasteCollector
from app.models.training import ModelVersion, SyntheticOutcome
from app.models.user import User
from app.models.wallet import Commission, WalletTxn

__all__ = [
    "AddressAccessEvent",
    "Booking",
    "ChatMessage",
    "ChatRead",
    "Commission",
    "CurrentNeed",
    "Donation",
    "DonationImage",
    "Handover",
    "ImpactRecord",
    "LogisticsProvider",
    "ModelVersion",
    "Match",
    "OrganizationProfile",
    "Payment",
    "RankingRun",
    "Recycling",
    "StatusEvent",
    "SyntheticOutcome",
    "User",
    "WalletTxn",
    "WasteCollector",
]
