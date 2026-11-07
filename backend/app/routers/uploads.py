import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..deps import audit, get_current_user_optional, rate_limit, require_reviewer
from ..models import ContaminationReport, UploadedEvidence, User

router = APIRouter(tags=["evidence"])
MAX_FILES_PER_REPORT = 3
ANON_WINDOW = timedelta(minutes=30)


def sniff_image(data: bytes) -> tuple[str, str] | None:
    """Detect type from file CONTENT (magic bytes), never from the client-supplied filename/MIME."""
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg", ".jpg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png", ".png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp", ".webp"
    return None


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


@router.post("/api/reports/{report_code}/evidence", status_code=201, dependencies=[Depends(rate_limit(10, 60))])
async def upload_evidence(report_code: str, file: UploadFile = File(...), db: Session = Depends(get_db),
                          user: User | None = Depends(get_current_user_optional)):
    r = db.scalar(select(ContaminationReport).where(ContaminationReport.report_code == report_code.upper()))
    if not r:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report not found")
    if r.reporter_id:
        if not user or user.id != r.reporter_id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the reporter can add evidence to this report")
    elif datetime.now(timezone.utc) - _aware(r.created_at) > ANON_WINDOW:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Anonymous reports accept photos only in the first 30 minutes")
    existing = db.scalar(select(func.count()).select_from(UploadedEvidence).where(UploadedEvidence.report_id == r.id))
    if existing >= MAX_FILES_PER_REPORT:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Maximum {MAX_FILES_PER_REPORT} photos per report")
    limit = settings.MAX_UPLOAD_MB * 1024 * 1024
    data = await file.read(limit + 1)
    if len(data) > limit:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, f"File exceeds {settings.MAX_UPLOAD_MB} MB")
    kind = sniff_image(data)
    if not kind:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Only JPEG, PNG or WebP images are allowed")
    content_type, ext = kind
    stored = uuid.uuid4().hex + ext  # random name: user-supplied filename is never used on disk
    folder = Path(settings.UPLOAD_DIR)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / stored).write_bytes(data)
    ev = UploadedEvidence(report_id=r.id, stored_name=stored, original_name=(file.filename or "photo")[:255],
                          content_type=content_type, size_bytes=len(data))
    db.add(ev)
    db.commit()
    return {"evidence_id": ev.id, "content_type": content_type, "size_bytes": len(data)}


@router.get("/api/admin/reports/{report_code}/evidence")
def list_evidence(report_code: str, _: User = Depends(require_reviewer), db: Session = Depends(get_db)):
    r = db.scalar(select(ContaminationReport).where(ContaminationReport.report_code == report_code.upper()))
    if not r:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report not found")
    rows = db.scalars(select(UploadedEvidence).where(UploadedEvidence.report_id == r.id))
    return [{"evidence_id": e.id, "content_type": e.content_type, "size_bytes": e.size_bytes,
             "created_at": e.created_at} for e in rows]


@router.get("/api/admin/evidence/{evidence_id}")
def download_evidence(evidence_id: str, actor: User = Depends(require_reviewer), db: Session = Depends(get_db)):
    """Evidence is never public: reviewers only, and every view is audit-logged."""
    e = db.get(UploadedEvidence, evidence_id)
    path = Path(settings.UPLOAD_DIR) / e.stored_name if e else None
    if not e or not path.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Evidence not found")
    audit(db, actor, "evidence.viewed", "uploaded_evidence", e.id)
    db.commit()
    return FileResponse(path, media_type=e.content_type, headers={"X-Content-Type-Options": "nosniff"})