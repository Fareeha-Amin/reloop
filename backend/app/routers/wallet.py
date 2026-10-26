from fastapi import APIRouter

from app.schemas.wallet import WalletOut, WalletTxnOut
from app.security.deps import DbSession, DonorUser
from app.services import wallet

router = APIRouter(prefix="/wallet", tags=["donor: wallet"])


@router.get("", response_model=WalletOut)
def get_wallet(user: DonorUser, db: DbSession):
    """The donor's wallet: an append-only ledger. The balance is SUM(amount), never
    stored. Credited by confirmed recycling settlements; spent, in full or in part, on
    a platform-arranged pickup; refunded if that pickup is cancelled before delivery.
    No withdrawals."""
    return WalletOut(balance=wallet.balance(db, user.id), transactions=[WalletTxnOut.model_validate(t) for t in wallet.ledger(db, user.id)])
