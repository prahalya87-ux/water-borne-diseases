import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (Boolean, DateTime, Enum, Float, ForeignKey, Index, Integer,
                        String, Text)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Role(str, enum.Enum):
    citizen = "citizen"
    healthcare_worker = "healthcare_worker"
    field_inspector = "field_inspector"
    administrator = "administrator"


class ReportStatus(str, enum.Enum):
    submitted = "submitted"
    under_review = "under_review"
    verification_required = "verification_required"
    verified = "verified"
    forwarded = "forwarded_to_authority"
    resolved = "resolved"
    rejected = "rejected"


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(Enum(Role), default=Role.citizen)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


class ContaminationReport(Base):
    """Citizen-submitted report. Stays UNVERIFIED until an authorised reviewer verifies it."""
    __tablename__ = "water_contamination_reports"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    report_code: Mapped[str] = mapped_column(String(20), unique=True, index=True)  # public tracking ID
    category: Mapped[str] = mapped_column(String(40), index=True)
    description: Mapped[str] = mapped_column(Text)
    locality: Mapped[str] = mapped_column(String(160))
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[ReportStatus] = mapped_column(Enum(ReportStatus), default=ReportStatus.submitted, index=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    possible_duplicate_of: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    # Private fields: never returned by public endpoints
    reporter_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    contact_info: Mapped[str | None] = mapped_column(String(255), nullable=True)
    consent_given: Mapped[bool] = mapped_column(Boolean, default=False)
    water_source: Mapped[str] = mapped_column(String(20), default="other")  # tap|borewell|tank|river|other
    pin_code: Mapped[str | None] = mapped_column(String(6), nullable=True, index=True)
    escalated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    escalation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    __table_args__ = (Index("ix_report_geo_time", "latitude", "longitude", "observed_at"),)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    actor_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    action: Mapped[str] = mapped_column(String(80), index=True)
    entity: Mapped[str] = mapped_column(String(60))
    entity_id: Mapped[str] = mapped_column(String(60))
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


# ===================== Phase 2b: remaining tables from the spec =====================
from datetime import date  # noqa: E402


class Timestamped:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


class RoleRef(Base):
    """Reference list of roles + descriptions. Authorization itself uses users.role (enum)."""
    __tablename__ = "roles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(40), unique=True)
    description: Mapped[str] = mapped_column(String(255))


class Location(Base, Timestamped):
    __tablename__ = "locations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(160), index=True)
    district: Mapped[str | None] = mapped_column(String(120), index=True, nullable=True)
    state: Mapped[str | None] = mapped_column(String(120), nullable=True)
    pin_code: Mapped[str | None] = mapped_column(String(10), index=True, nullable=True)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)


class DiseaseReport(Base, Timestamped):
    """Aggregated surveillance record. verification_status says whether an authority confirmed it."""
    __tablename__ = "disease_reports"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    disease: Mapped[str] = mapped_column(String(60), index=True)
    cases: Mapped[int | None] = mapped_column(Integer, nullable=True)
    locality: Mapped[str] = mapped_column(String(160), index=True)
    district: Mapped[str | None] = mapped_column(String(120), index=True, nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    reported_on: Mapped[date] = mapped_column(index=True)
    source: Mapped[str] = mapped_column(String(160))
    verification_status: Mapped[str] = mapped_column(String(30), default="unverified")  # unverified | media_reported | verified
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)


class WaterQualityTest(Base, Timestamped):
    __tablename__ = "water_quality_tests"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    sample_id: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    locality: Mapped[str] = mapped_column(String(160), index=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    tested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    organization: Mapped[str] = mapped_column(String(160))
    ph: Mapped[float | None] = mapped_column(Float, nullable=True)
    turbidity_ntu: Mapped[float | None] = mapped_column(Float, nullable=True)
    tds_mg_l: Mapped[float | None] = mapped_column(Float, nullable=True)
    residual_chlorine_mg_l: Mapped[float | None] = mapped_column(Float, nullable=True)
    ecoli_result: Mapped[str] = mapped_column(String(20), default="not_tested")  # absent | present | not_tested
    verification_status: Mapped[str] = mapped_column(String(30), default="user_submitted")
    # laboratory_confirmed | unverified_sensor | user_submitted
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    recorded_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)


class HealthcareFacility(Base, Timestamped):
    """Phone/hours/beds are nullable on purpose: never invent them."""
    __tablename__ = "healthcare_facilities"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(200), index=True)
    facility_type: Mapped[str] = mapped_column(String(40), index=True)  # hospital | clinic | public_health_centre
    address: Mapped[str | None] = mapped_column(String(300), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    opening_hours: Mapped[str | None] = mapped_column(String(200), nullable=True)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(160))
    last_verified_on: Mapped[date | None] = mapped_column(nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)

    __table_args__ = (Index("ix_facility_geo", "latitude", "longitude"),)


class OfficialAlert(Base, Timestamped):
    __tablename__ = "official_alerts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(String(200))
    locality: Mapped[str] = mapped_column(String(160), index=True)
    district: Mapped[str | None] = mapped_column(String(120), nullable=True)
    severity: Mapped[str] = mapped_column(String(20))  # info | advisory | warning | critical
    description: Mapped[str] = mapped_column(Text)
    recommended_action: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(200))
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    verification_status: Mapped[str] = mapped_column(String(30))
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)
    created_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    approval_status: Mapped[str] = mapped_column(String(20), default="approved", index=True)  # pending_approval|approved|rejected
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class UserSubscription(Base):
    __tablename__ = "user_subscriptions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    locality: Mapped[str] = mapped_column(String(160), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(20), default="info")
    link: Mapped[str | None] = mapped_column(String(300), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)


class RiskAssessment(Base):
    """Score is nullable: 'insufficient_data' must be representable. Not a validated probability."""
    __tablename__ = "risk_assessments"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    locality: Mapped[str] = mapped_column(String(160), index=True)
    category: Mapped[str] = mapped_column(String(30))  # low | moderate | high | insufficient_data
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    factors_json: Mapped[str] = mapped_column(Text, default="[]")
    period_start: Mapped[date | None] = mapped_column(nullable=True)
    period_end: Mapped[date | None] = mapped_column(nullable=True)
    confidence: Mapped[str] = mapped_column(String(20), default="low")
    limitations: Mapped[str] = mapped_column(Text, default="")
    method: Mapped[str] = mapped_column(String(60), default="rule_based_v1")
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    analysed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Inspection(Base, Timestamped):
    __tablename__ = "inspections"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    inspector_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    locality: Mapped[str] = mapped_column(String(160))
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    inspected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str] = mapped_column(Text)
    report_code: Mapped[str | None] = mapped_column(String(20), nullable=True)


class UploadedEvidence(Base):
    __tablename__ = "uploaded_evidence"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    report_id: Mapped[str] = mapped_column(ForeignKey("water_contamination_reports.id"), index=True)
    stored_name: Mapped[str] = mapped_column(String(80), unique=True)
    original_name: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(40))
    size_bytes: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class ServicePoint(Base, Timestamped):
    """Water-testing labs, public water points, purification facilities, municipal complaint services.
    Contact/hours are nullable: never invented. Complaint services may have no coordinates (coverage_area)."""
    __tablename__ = "service_points"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    category: Mapped[str] = mapped_column(String(30), index=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    address: Mapped[str | None] = mapped_column(String(300), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    opening_hours: Mapped[str | None] = mapped_column(String(200), nullable=True)
    website: Mapped[str | None] = mapped_column(String(300), nullable=True)
    coverage_area: Mapped[str | None] = mapped_column(String(200), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(200))
    last_verified_on: Mapped[date | None] = mapped_column(nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)

    __table_args__ = (Index("ix_service_geo", "latitude", "longitude"),)