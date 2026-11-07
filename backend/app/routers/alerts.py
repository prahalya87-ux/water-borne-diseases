from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import audit, get_current_user, require_admin, require_roles
from ..models import Notification, OfficialAlert, Role, User, UserSubscription
from ..notify import notify_users

router = APIRouter(tags=["alerts"])


class AlertIn(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    locality: str = Field(min_length=2, max_length=160)
    district: str | None = Field(default=None, max_length=120)
    severity: Literal["info", "advisory", "warning", "critical"]
    description: str = Field(min_length=10, max_length=3000)
    recommended_action: str = Field(min_length=5, max_length=2000)
    source: str = Field(min_length=2, max_length=200)
    source_url: str | None = Field(default=None, max_length=500)
    verification_status: Literal["official"]


class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    title: str
    locality: str
    district: str | None
    severity: str
    description: str
    recommended_action: str
    source: str
    source_url: str | None
    verification_status: str
    is_demo: bool
    approval_status: str
    published_at: datetime


class SubscriptionIn(BaseModel):
    locality: str = Field(min_length=2, max_length=160)


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    title: str
    body: str
    severity: str
    link: str | None
    is_read: bool
    created_at: datetime


@router.get("/api/alerts", response_model=list[AlertOut])
def list_alerts(locality: str | None = None, limit: int = 50, offset: int = 0, db: Session = Depends(get_db)):
    q = select(OfficialAlert).where(OfficialAlert.approval_status == "approved", OfficialAlert.is_demo.is_(False)).order_by(OfficialAlert.published_at.desc()).limit(max(1, min(limit, 200))).offset(offset)
    if locality:
        q = q.where(func.lower(OfficialAlert.locality) == locality.strip().lower())
    return list(db.scalars(q))


@router.post("/api/admin/alerts", response_model=AlertOut, status_code=201)
def create_alert(body: AlertIn, actor: User = Depends(require_admin), db: Session = Depends(get_db)):
    alert = OfficialAlert(**body.model_dump(), is_demo=False, created_by=actor.id, approval_status="approved",
                          approved_by=actor.id, approved_at=datetime.now(timezone.utc))
    db.add(alert)
    db.flush()
    subs = db.scalars(select(UserSubscription.user_id).where(
        func.lower(UserSubscription.locality) == body.locality.strip().lower()))
    notify_users(db, subs, body.title, body.recommended_action, body.severity, "/alerts")
    audit(db, actor, "alert.created", "official_alert", alert.id, f"{body.severity} / {body.locality}")
    db.commit()
    db.refresh(alert)
    return alert


@router.post("/api/subscriptions", status_code=201)
def subscribe(body: SubscriptionIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    loc = body.locality.strip()
    dup = db.scalar(select(UserSubscription).where(
        UserSubscription.user_id == user.id, func.lower(UserSubscription.locality) == loc.lower()))
    if dup:
        raise HTTPException(status.HTTP_409_CONFLICT, "Already subscribed to this locality")
    sub = UserSubscription(user_id=user.id, locality=loc)
    db.add(sub)
    db.commit()
    return {"id": sub.id, "locality": sub.locality}


@router.get("/api/subscriptions")
def my_subscriptions(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(UserSubscription).where(UserSubscription.user_id == user.id))
    return [{"id": s.id, "locality": s.locality} for s in rows]


@router.delete("/api/subscriptions/{sub_id}", status_code=204)
def unsubscribe(sub_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    s = db.get(UserSubscription, sub_id)
    if not s or s.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Subscription not found")
    db.delete(s)
    db.commit()


@router.get("/api/notifications", response_model=list[NotificationOut])
def my_notifications(unread_only: bool = False, limit: int = 50, offset: int = 0,
                     user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = select(Notification).where(Notification.user_id == user.id).order_by(Notification.created_at.desc()) \
        .limit(max(1, min(limit, 200))).offset(offset)
    if unread_only:
        q = q.where(Notification.is_read.is_(False))
    return list(db.scalars(q))


@router.post("/api/notifications/{notification_id}/read", response_model=NotificationOut)
def mark_read(notification_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    n = db.get(Notification, notification_id)
    if not n or n.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Notification not found")
    n.is_read = True
    db.commit()
    db.refresh(n)
    return n


# ---------------- Approval workflow: drafts -> admin approval -> public + subscriber notifications ----------------

class DraftIn(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    locality: str = Field(min_length=2, max_length=160)
    district: str | None = Field(default=None, max_length=120)
    severity: Literal["info", "advisory", "warning", "critical"]
    description: str = Field(min_length=10, max_length=3000)
    recommended_action: str = Field(min_length=5, max_length=2000)
    source: str = Field(min_length=2, max_length=200)
    source_url: str | None = Field(default=None, max_length=500)


class ApproveIn(BaseModel):
    verification_status: Literal["official", "unverified_draft"] | None = None


class RejectIn(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


def _publish_notifications(db: Session, alert: OfficialAlert):
    subs = db.scalars(select(UserSubscription.user_id).where(
        func.lower(UserSubscription.locality) == alert.locality.strip().lower()))
    label = "[UNVERIFIED] " if alert.verification_status == "unverified_draft" else ""
    notify_users(db, subs, f"{label}{alert.title}", alert.recommended_action, alert.severity, "/alerts")


@router.post("/api/alert-drafts", response_model=AlertOut, status_code=201)
def create_draft(body: DraftIn, actor: User = Depends(require_roles(Role.administrator, Role.field_inspector, Role.healthcare_worker)),
                 db: Session = Depends(get_db)):
    """Staff propose an alert. It stays private until an administrator approves it."""
    alert = OfficialAlert(**body.model_dump(), verification_status="unverified_draft", approval_status="pending_approval",
                          is_demo=False, created_by=actor.id)
    db.add(alert)
    db.flush()
    admins = list(db.scalars(select(User.id).where(User.role == Role.administrator, User.is_active.is_(True))))
    notify_users(db, admins, "Alert awaiting approval", f"{body.title} ({body.locality})", "advisory", "/admin/alerts/pending")
    audit(db, actor, "alert.draft_created", "official_alert", alert.id, body.locality)
    db.commit()
    db.refresh(alert)
    return alert


@router.get("/api/admin/alerts/pending", response_model=list[AlertOut])
def pending_alerts(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    q = select(OfficialAlert).where(OfficialAlert.approval_status == "pending_approval", OfficialAlert.is_demo.is_(False)).order_by(OfficialAlert.created_at.desc())
    return list(db.scalars(q))


@router.post("/api/admin/alerts/{alert_id}/approve", response_model=AlertOut)
def approve_alert(alert_id: str, body: ApproveIn | None = None, actor: User = Depends(require_admin),
                  db: Session = Depends(get_db)):
    a = db.get(OfficialAlert, alert_id)
    if not a:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Alert not found")
    if a.approval_status != "pending_approval":
        raise HTTPException(status.HTTP_409_CONFLICT, "Alert is not awaiting approval")
    if body and body.verification_status:
        a.verification_status = body.verification_status
    a.approval_status, a.approved_by, a.approved_at = "approved", actor.id, datetime.now(timezone.utc)
    a.published_at = a.approved_at
    _publish_notifications(db, a)
    audit(db, actor, "alert.approved", "official_alert", a.id, a.verification_status)
    db.commit()
    db.refresh(a)
    return a


@router.post("/api/admin/alerts/{alert_id}/reject", response_model=AlertOut)
def reject_alert(alert_id: str, body: RejectIn, actor: User = Depends(require_admin), db: Session = Depends(get_db)):
    a = db.get(OfficialAlert, alert_id)
    if not a:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Alert not found")
    if a.approval_status != "pending_approval":
        raise HTTPException(status.HTTP_409_CONFLICT, "Alert is not awaiting approval")
    a.approval_status, a.rejection_reason = "rejected", body.reason
    audit(db, actor, "alert.rejected", "official_alert", a.id, body.reason)
    db.commit()
    db.refresh(a)
    return a