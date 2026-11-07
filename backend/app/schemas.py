from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from .models import ReportStatus, Role

CATEGORIES = Literal[
    "unusual_color", "unusual_odor", "visible_contamination", "suspected_illness_cluster",
    "sewage_mixing", "leakage_near_drainage", "suspected_contamination", "illness_concern",
    "damaged_infrastructure",
]
WATER_SOURCES = Literal["tap", "borewell", "tank", "river", "other"]


class RegisterIn(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=8, max_length=128)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    email: EmailStr
    full_name: str
    role: Role


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class ReportIn(BaseModel):
    category: CATEGORIES
    water_source: WATER_SOURCES = "other"
    description: str | None = Field(default=None, max_length=2000)
    locality: str | None = Field(default=None, max_length=160)
    pin_code: str | None = Field(default=None, pattern=r"^[1-9][0-9]{5}$")
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    observed_at: datetime
    contact_info: str | None = Field(default=None, max_length=255)
    consent_given: bool


class PublicReportOut(BaseModel):
    """Safe for public view: no reporter or contact details."""
    model_config = ConfigDict(from_attributes=True)
    report_code: str
    category: str
    water_source: str
    locality: str
    pin_code: str | None = None
    status: ReportStatus
    rejection_reason: str | None = None
    observed_at: datetime
    created_at: datetime
    is_demo: bool
    verification_label: str = "Unverified citizen report"


class AdminReportOut(PublicReportOut):
    """Reviewers only (server-side role check). Includes private fields."""
    description: str
    latitude: float | None = None
    longitude: float | None = None
    contact_info: str | None = None
    possible_duplicate_of: str | None = None
    escalated_at: datetime | None = None
    escalation_reason: str | None = None


class StatusUpdateIn(BaseModel):
    status: ReportStatus
    rejection_reason: str | None = Field(default=None, max_length=500)


class ErrorOut(BaseModel):
    error: str
    detail: str | None = None