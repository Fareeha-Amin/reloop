from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.config import get_settings
from app.models import User
from app.routers.common import GeocoderDep
from app.schemas.auth import AccessToken, RefreshRequest, TokenPair
from app.schemas.organization import AcceptorRegister, AcceptorRegistered
from app.schemas.user import DonorRegister, UserOut
from app.security.deps import CurrentUser, DbSession
from app.security.tokens import InvalidToken, TokenType, create_token, decode_token
from app.services import users

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register/donor", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register_donor(data: DonorRegister, db: DbSession):
    return users.register_donor(db, data)


@router.post(
    "/register/acceptor",
    response_model=AcceptorRegistered,
    status_code=status.HTTP_201_CREATED,
)
def register_acceptor(data: AcceptorRegister, db: DbSession, geocoder: GeocoderDep):
    user, org = users.register_acceptor(db, data, geocoder)
    return AcceptorRegistered(user=user, organization=org)


@router.post("/login", response_model=TokenPair)
def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], db: DbSession):
    """OAuth2 password flow. `username` is the account's email address."""
    user = users.authenticate(db, form.username, form.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    secret = get_settings().secret_key
    return TokenPair(
        access_token=create_token(user.id, TokenType.ACCESS, secret),
        refresh_token=create_token(user.id, TokenType.REFRESH, secret),
    )


@router.post("/refresh", response_model=AccessToken)
def refresh(data: RefreshRequest, db: DbSession):
    """Exchange a refresh token for a new access token. Stateless: refresh tokens are
    not rotated or revocable (see README, Known limitations)."""
    secret = get_settings().secret_key
    try:
        claims = decode_token(data.refresh_token, TokenType.REFRESH, secret)
    except InvalidToken as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    if db.get(User, claims.user_id) is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer exists.")
    return AccessToken(access_token=create_token(claims.user_id, TokenType.ACCESS, secret))


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser):
    return user
