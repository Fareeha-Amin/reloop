from fastapi import APIRouter

from app.routers.common import PageDep
from app.schemas.notification import NotificationOut
from app.security.deps import CurrentUser, DbSession
from app.services import notifications

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationOut])
def list_notifications(user: CurrentUser, db: DbSession, page: PageDep):
    """Status events on donations you are party to, newest first. In-app only: derived
    from the audit log on each request, with no push or email (see README). Poll it."""
    return notifications.feed(db, user, page.limit, page.offset)
