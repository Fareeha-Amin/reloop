import uuid
from datetime import datetime
from typing import Annotated

from pydantic import EmailStr, StringConstraints

from app.constants import PASSWORD_MAX_LENGTH, PASSWORD_MIN_LENGTH, Role
from app.schemas.common import InputModel, Name, OutputModel, Phone

Password = Annotated[
    str, StringConstraints(min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH)
]


class DonorRegister(InputModel):
    email: EmailStr
    password: Password
    full_name: Name
    phone: Phone


class AdminCreate(InputModel):
    """Used by the CLI only; there is no admin registration endpoint."""

    email: EmailStr
    password: Password
    full_name: Name


class UserOut(OutputModel):
    id: uuid.UUID
    email: str
    role: Role
    full_name: str
    phone: str | None
    created_at: datetime
