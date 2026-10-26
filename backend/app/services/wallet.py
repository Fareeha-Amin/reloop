"""A donor's wallet: an append-only ledger (app.models.WalletTxn). The balance is
derived (SUM(amount)), never stored. No withdrawals."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.constants import WalletTxnType
from app.models import WalletTxn

_PAISE = Decimal("0.01")


def balance(db: Session, donor_id: uuid.UUID) -> Decimal:
    total = db.scalar(select(func.coalesce(func.sum(WalletTxn.amount), 0)).where(WalletTxn.donor_id == donor_id))
    return Decimal(total).quantize(_PAISE)


def ledger(db: Session, donor_id: uuid.UUID) -> list[WalletTxn]:
    return list(
        db.scalars(
            select(WalletTxn).where(WalletTxn.donor_id == donor_id).order_by(WalletTxn.created_at.desc())
        )
    )


def record(
    db: Session,
    donor_id: uuid.UUID,
    type_: WalletTxnType,
    amount: Decimal,
    now: datetime,
    *,
    reference_recycling_id: uuid.UUID | None = None,
    reference_booking_id: uuid.UUID | None = None,
    note: str | None = None,
) -> WalletTxn:
    """amount is signed: positive credits the donor, negative debits them."""
    txn = WalletTxn(
        donor_id=donor_id,
        type=type_,
        amount=amount,
        reference_recycling_id=reference_recycling_id,
        reference_booking_id=reference_booking_id,
        note=note,
        created_at=now,
    )
    db.add(txn)
    return txn
