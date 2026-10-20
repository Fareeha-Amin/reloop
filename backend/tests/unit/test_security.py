import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.constants import ACCESS_TOKEN_TTL_MINUTES, JWT_ALGORITHM, REFRESH_TOKEN_TTL_DAYS
from app.security.passwords import hash_password, verify_password
from app.security.tokens import InvalidToken, TokenType, create_token, decode_token

SECRET = "unit-test-secret-of-sufficient-length-for-hs256"
NOW = datetime(2026, 10, 20, 12, 0, tzinfo=UTC)
USER = uuid.uuid4()


def test_password_hash_is_argon2_and_verifies():
    hashed = hash_password("correct-horse-battery")
    assert hashed.startswith("$argon2")
    assert verify_password("correct-horse-battery", hashed)
    assert not verify_password("wrong-password", hashed)


def test_password_hashes_are_salted():
    assert hash_password("same-password") != hash_password("same-password")


def test_access_token_round_trip():
    token = create_token(USER, TokenType.ACCESS, SECRET, now=NOW)
    claims = decode_token(token, TokenType.ACCESS, SECRET, now=NOW)
    assert claims.user_id == USER
    assert claims.expires_at == NOW + timedelta(minutes=ACCESS_TOKEN_TTL_MINUTES)


def test_refresh_token_lives_longer():
    token = create_token(USER, TokenType.REFRESH, SECRET, now=NOW)
    claims = decode_token(token, TokenType.REFRESH, SECRET, now=NOW)
    assert claims.expires_at == NOW + timedelta(days=REFRESH_TOKEN_TTL_DAYS)


def test_token_types_are_not_interchangeable():
    refresh = create_token(USER, TokenType.REFRESH, SECRET, now=NOW)
    access = create_token(USER, TokenType.ACCESS, SECRET, now=NOW)
    with pytest.raises(InvalidToken):
        decode_token(refresh, TokenType.ACCESS, SECRET, now=NOW)
    with pytest.raises(InvalidToken):
        decode_token(access, TokenType.REFRESH, SECRET, now=NOW)


def test_expired_token_rejected():
    token = create_token(USER, TokenType.ACCESS, SECRET, now=NOW)
    later = NOW + timedelta(minutes=ACCESS_TOKEN_TTL_MINUTES)
    with pytest.raises(InvalidToken, match="expired"):
        decode_token(token, TokenType.ACCESS, SECRET, now=later)


def test_wrong_secret_rejected():
    token = create_token(USER, TokenType.ACCESS, SECRET, now=NOW)
    with pytest.raises(InvalidToken):
        decode_token(token, TokenType.ACCESS, SECRET + "x", now=NOW)


def test_unsigned_token_rejected():
    payload = {"sub": str(USER), "typ": "access", "iat": NOW, "exp": NOW + timedelta(hours=1)}
    forged = jwt.encode(payload, key=None, algorithm="none")
    with pytest.raises(InvalidToken):
        decode_token(forged, TokenType.ACCESS, SECRET, now=NOW)


def test_token_missing_subject_rejected():
    payload = {"typ": "access", "iat": NOW, "exp": NOW + timedelta(hours=1)}
    token = jwt.encode(payload, SECRET, algorithm=JWT_ALGORITHM)
    with pytest.raises(InvalidToken):
        decode_token(token, TokenType.ACCESS, SECRET, now=NOW)
