"""JWT access and refresh tokens. Pure functions: the secret and the clock are arguments.

Stateless by design: there is no server-side session and no revocation list. A token
stays valid until it expires, even after a password change. The README states this.

Tokens carry only the user id and the token type. The role is read from the database on
every request, so a role change takes effect immediately.
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum

import jwt

from app.constants import ACCESS_TOKEN_TTL_MINUTES, JWT_ALGORITHM, REFRESH_TOKEN_TTL_DAYS


class TokenType(StrEnum):
    ACCESS = "access"
    REFRESH = "refresh"


TOKEN_TTL = {
    TokenType.ACCESS: timedelta(minutes=ACCESS_TOKEN_TTL_MINUTES),
    TokenType.REFRESH: timedelta(days=REFRESH_TOKEN_TTL_DAYS),
}


class InvalidToken(Exception):
    pass


@dataclass(frozen=True)
class TokenClaims:
    user_id: uuid.UUID
    token_type: TokenType
    expires_at: datetime


def create_token(
    user_id: uuid.UUID, token_type: TokenType, secret: str, now: datetime | None = None
) -> str:
    issued_at = now or datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "typ": token_type.value,
        "iat": issued_at,
        "exp": issued_at + TOKEN_TTL[token_type],
    }
    return jwt.encode(payload, secret, algorithm=JWT_ALGORITHM)


def decode_token(
    token: str, expected_type: TokenType, secret: str, now: datetime | None = None
) -> TokenClaims:
    """Verify signature, expiry and type. Raises InvalidToken on any failure."""
    try:
        # Time claims are checked below against `now`, so tests can control the clock.
        payload = jwt.decode(
            token,
            secret,
            algorithms=[JWT_ALGORITHM],
            options={
                "require": ["sub", "typ", "exp", "iat"],
                "verify_exp": False,
                "verify_iat": False,
            },
        )
    except jwt.PyJWTError as exc:
        raise InvalidToken("Token is invalid.") from exc

    current = now or datetime.now(UTC)
    if current.timestamp() >= payload["exp"]:
        raise InvalidToken("Token has expired.")
    if payload.get("typ") != expected_type.value:
        raise InvalidToken(f"Expected a {expected_type.value} token.")
    try:
        user_id = uuid.UUID(payload["sub"])
    except (ValueError, TypeError) as exc:
        raise InvalidToken("Token subject is invalid.") from exc
    return TokenClaims(
        user_id=user_id,
        token_type=expected_type,
        expires_at=datetime.fromtimestamp(payload["exp"], UTC),
    )
