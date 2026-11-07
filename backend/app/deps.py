import time
from collections import defaultdict, deque

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .database import get_db
from .models import AuditLog, Role, User
from .security import decode_token

bearer = HTTPBearer(auto_error=False)


def get_current_user_optional(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User | None:
    if not creds:
        return None
    payload = decode_token(creds.credentials)
    if not payload:
        return None
    user = db.get(User, payload.get("sub"))
    return user if user and user.is_active else None


def get_current_user(user: User | None = Depends(get_current_user_optional)) -> User:
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentication required")
    return user


def require_roles(*roles: Role):
    """Server-side authorization. Hiding buttons in the UI is NOT security; this is."""
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "You do not have permission for this action")
        return user
    return checker


require_admin = require_roles(Role.administrator)
require_reviewer = require_roles(Role.administrator, Role.field_inspector)


def audit(db: Session, actor: User | None, action: str, entity: str, entity_id: str, detail: str | None = None):
    db.add(AuditLog(actor_id=actor.id if actor else None, action=action, entity=entity,
                    entity_id=entity_id, detail=detail))


# Simple in-memory sliding-window rate limiter (single-process; use Redis in production).
_hits: dict[str, deque] = defaultdict(deque)


def rate_limit(max_calls: int, window_s: int):
    def limiter(request: Request):
        key = f"{request.url.path}:{request.client.host if request.client else 'unknown'}"
        now = time.monotonic()
        q = _hits[key]
        while q and now - q[0] > window_s:
            q.popleft()
        if len(q) >= max_calls:
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many requests. Please try again later.")
        q.append(now)
    return limiter


def reset_rate_limits():
    _hits.clear()