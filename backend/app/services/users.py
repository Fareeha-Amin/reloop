from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants import Role
from app.models import OrganizationProfile, User
from app.schemas.organization import AcceptorRegister
from app.schemas.user import DonorRegister
from app.security.passwords import burn_verification_time, hash_password, verify_password
from app.services.errors import Conflict
from app.services.geocoding import Geocoder


def normalise_email(email: str) -> str:
    return email.strip().lower()


def get_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == normalise_email(email)))


def _new_user(
    db: Session, *, email: str, password: str, role: Role, full_name: str, phone: str | None
) -> User:
    if get_by_email(db, email) is not None:
        raise Conflict("An account with this email already exists.")
    user = User(
        email=normalise_email(email),
        password_hash=hash_password(password),
        role=role,
        full_name=full_name,
        phone=phone,
    )
    db.add(user)
    return user


def register_donor(db: Session, data: DonorRegister) -> User:
    user = _new_user(
        db,
        email=data.email,
        password=data.password,
        role=Role.DONOR,
        full_name=data.full_name,
        phone=data.phone,
    )
    db.commit()
    return user


def register_acceptor(
    db: Session, data: AcceptorRegister, geocoder: Geocoder
) -> tuple[User, OrganizationProfile]:
    """User and organisation profile are created in one transaction: neither exists
    without the other. The organisation starts PENDING (the column default)."""
    org_in = data.organization
    if db.scalar(
        select(OrganizationProfile.id).where(
            OrganizationProfile.registration_id == org_in.registration_id
        )
    ):
        raise Conflict("An organisation with this registration ID already exists.")

    location = geocoder.resolve(org_in.address_text, org_in.latitude, org_in.longitude)
    user = _new_user(
        db,
        email=data.email,
        password=data.password,
        role=Role.ACCEPTOR,
        full_name=data.full_name,
        phone=data.phone,
    )
    org = OrganizationProfile(
        user=user,
        name=org_in.name,
        registration_id=org_in.registration_id,
        contact_person=org_in.contact_person,
        phone=org_in.phone,
        address_text=location.address_text,
        latitude=location.latitude,
        longitude=location.longitude,
        pickup_capable=org_in.pickup_capable,
        storage_capacity=org_in.storage_capacity,
        categories_accepted=list(org_in.categories_accepted),
    )
    db.add(org)
    db.commit()
    return user, org


def create_admin(db: Session, *, email: str, password: str, full_name: str) -> User:
    """Admins cannot self-register; this is called only by the CLI (app.cli)."""
    user = _new_user(
        db, email=email, password=password, role=Role.ADMIN, full_name=full_name, phone=None
    )
    db.commit()
    return user


def authenticate(db: Session, email: str, password: str) -> User | None:
    user = get_by_email(db, email)
    if user is None:
        burn_verification_time(password)
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user
