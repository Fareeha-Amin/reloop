from pydantic import BaseModel

from app.schemas.common import InputModel


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AccessToken(BaseModel):
    """Refreshing issues a new access token only. The refresh token is not extended, so a
    session ends when the refresh token expires, however active it has been."""

    access_token: str
    token_type: str = "bearer"


class RefreshRequest(InputModel):
    refresh_token: str
