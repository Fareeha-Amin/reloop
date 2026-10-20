from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.constants import Role
from app.db import Base, StrEnumType, Timestamps, UUIDPrimaryKey

if TYPE_CHECKING:
    from app.models.organization import OrganizationProfile


class User(UUIDPrimaryKey, Timestamps, Base):
    __tablename__ = "users"

    # Stored lowercased (normalised in app.services.users), so the unique index is
    # effectively case-insensitive.
    email: Mapped[str] = mapped_column(String(320), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(StrEnumType(Role))
    full_name: Mapped[str] = mapped_column(String(200))
    # Required for donors and acceptors at the API edge; admins may have none.
    phone: Mapped[str | None] = mapped_column(String(32))

    organization: Mapped["OrganizationProfile | None"] = relationship(
        back_populates="user", foreign_keys="OrganizationProfile.user_id"
    )
