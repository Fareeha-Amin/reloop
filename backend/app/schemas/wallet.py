import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import Field

from app.constants import CURRENCY, WalletTxnType
from app.schemas.common import OutputModel


class WalletTxnOut(OutputModel):
    id: uuid.UUID
    type: WalletTxnType
    amount: Decimal = Field(description="Signed: positive credits the donor, negative debits them.")
    reference_recycling_id: uuid.UUID | None
    reference_booking_id: uuid.UUID | None
    note: str | None
    created_at: datetime


class WalletOut(OutputModel):
    """The balance is derived (SUM of the ledger), never stored. No withdrawals."""

    balance: Decimal
    currency: str = CURRENCY
    transactions: list[WalletTxnOut]
