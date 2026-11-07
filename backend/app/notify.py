from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Notification, Role, User


def notify_users(db: Session, user_ids, title: str, body: str, severity: str = "info", link: str | None = None):
    """Create in-app notifications. Caller commits. Email/push can be added as extra delivery channels here."""
    for uid in set(user_ids):
        db.add(Notification(user_id=uid, title=title, body=body, severity=severity, link=link))


def reviewer_ids(db: Session) -> list[str]:
    q = select(User.id).where(User.role.in_([Role.administrator, Role.field_inspector]), User.is_active.is_(True))
    return list(db.scalars(q))