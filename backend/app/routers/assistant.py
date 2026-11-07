from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..assistant import DISCLAIMER, reply
from ..database import get_db
from ..deps import rate_limit
from ..models import OfficialAlert
from ..risk import latest_per_locality

router = APIRouter(tags=["assistant"])


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=500)
    locality: str | None = Field(default=None, max_length=160)


def _context(db: Session, locality: str) -> list[str]:
    loc = locality.strip()
    alerts = list(db.scalars(select(OfficialAlert).where(OfficialAlert.approval_status == "approved",
                                                         OfficialAlert.is_demo.is_(False),
                                                         func.lower(OfficialAlert.locality) == loc.lower())
                             .order_by(OfficialAlert.published_at.desc()).limit(3)))
    notes = []
    if alerts:
        def tag(a):
            return "unverified" if a.verification_status == "unverified_draft" else "official"
        notes.append(f"Published alerts for {loc}: " + "; ".join(f"{a.title} ({tag(a)})" for a in alerts) + ". See the Alerts page for details.")
    else:
        notes.append(f"WaterGuard has no published alert for {loc}. That does not mean the water is safe: check with your local water authority.")
    for r in latest_per_locality(db):
        if r.locality.strip().lower() == loc.lower() and r.category != "insufficient_data":
            notes.append(f"Our rule-based screening currently rates {loc} as {r.category} risk. This is an unvalidated estimate, not a confirmed outbreak.")
    return notes


@router.post("/api/assistant/chat", dependencies=[Depends(rate_limit(30, 60))])
def chat(body: ChatIn, db: Session = Depends(get_db)):
    out = reply(body.message)
    out["context_notes"] = _context(db, body.locality) if body.locality and body.locality.strip() and not out["emergency"] else []
    out["disclaimer"] = DISCLAIMER
    return out