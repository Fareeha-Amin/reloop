"""Route-level auth dependencies. Roles are enforced per route, never via an is_staff flag.

401 — no token, or an invalid/expired one.
403 — authenticated, but the route does not allow this role.
"""

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.config import get_settings
from app.constants import Role
from app.db import get_db
from app.models import User
from app.security.tokens import InvalidToken, TokenType, decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

DbSession = Annotated[Session, Depends(get_db)]


def _unauthorised(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], db: DbSession) -> User:
    try:
        claims = decode_token(token, TokenType.ACCESS, get_settings().secret_key)
    except InvalidToken as exc:
        raise _unauthorised(str(exc)) from exc
    user = db.get(User, claims.user_id)
    if user is None:
        raise _unauthorised("User no longer exists.")
    return user


def require_role(*roles: Role) -> Callable[[User], User]:
    allowed = frozenset(roles)

    def dependency(user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This action requires role: {', '.join(sorted(allowed))}.",
            )
        return user

    return dependency


CurrentUser = Annotated[User, Depends(get_current_user)]
DonorUser = Annotated[User, Depends(require_role(Role.DONOR))]
AcceptorUser = Annotated[User, Depends(require_role(Role.ACCEPTOR))]
AdminUser = Annotated[User, Depends(require_role(Role.ADMIN))]
DonorOrAdminUser = Annotated[User, Depends(require_role(Role.DONOR, Role.ADMIN))]
