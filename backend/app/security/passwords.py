"""Password hashing with Argon2 (pwdlib). Not passlib."""

from functools import lru_cache

from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

_hasher = PasswordHash((Argon2Hasher(),))


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _hasher.verify(password, password_hash)


@lru_cache
def _dummy_hash() -> str:
    return _hasher.hash("timing-equaliser-not-a-real-password")


def burn_verification_time(password: str) -> None:
    """Spend the same time as a real check when the email is unknown, so login timing
    does not reveal which emails are registered."""
    _hasher.verify(password, _dummy_hash())
