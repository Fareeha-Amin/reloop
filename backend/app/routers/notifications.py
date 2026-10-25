from fastapi import APIRouter

from app.routers.common import PageDep
from app.schemas.notification import NotificationOut
from app.security.deps import CurrentUser, DbSession
from app.services import notifications

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationOut])
def list_notifications(user: CurrentUser, db: DbSession, page: PageDep):
    """Newest first: status events on donations you are party to, chat messages from the
    other party in threads you can read, and (admins) organisation registrations. In-app
    only: derived on each request, with no push or email and no server-side read state
    (see README). Poll it, and track read items by `key`."""
    return notifications.feed(db, user, page.limit, page.offset)
