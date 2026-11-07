"""Add model columns missing from existing SQLite databases."""

from alembic import op
import sqlalchemy as sa

revision = "20261027_01"
down_revision = None
branch_labels = None
depends_on = None


def _add_column_if_missing(table: str, column: sa.Column) -> None:
    inspector = sa.inspect(op.get_bind())
    if table not in inspector.get_table_names():
        return
    existing = {item["name"] for item in inspector.get_columns(table)}
    if column.name not in existing:
        op.add_column(table, column)


def upgrade() -> None:
    _add_column_if_missing(
        "water_contamination_reports",
        sa.Column("water_source", sa.String(length=20), nullable=False, server_default=sa.text("'other'")),
    )
    _add_column_if_missing("water_contamination_reports", sa.Column("pin_code", sa.String(length=6), nullable=True))
    _add_column_if_missing(
        "water_contamination_reports",
        sa.Column("escalated_at", sa.DateTime(timezone=True), nullable=True),
    )
    _add_column_if_missing("water_contamination_reports", sa.Column("escalation_reason", sa.Text(), nullable=True))
    _add_column_if_missing("disease_reports", sa.Column("source_url", sa.String(length=500), nullable=True))
    _add_column_if_missing("disease_reports", sa.Column("notes", sa.Text(), nullable=True))
    _add_column_if_missing("healthcare_facilities", sa.Column("opening_hours", sa.String(length=200), nullable=True))
    _add_column_if_missing(
        "official_alerts",
        sa.Column("approval_status", sa.String(length=20), nullable=False, server_default=sa.text("'approved'")),
    )
    _add_column_if_missing("official_alerts", sa.Column("rejection_reason", sa.Text(), nullable=True))
    _add_column_if_missing("official_alerts", sa.Column("approved_by", sa.String(length=36), nullable=True))
    _add_column_if_missing("official_alerts", sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    for table, columns in (
        ("official_alerts", ("approved_at", "approved_by", "rejection_reason", "approval_status")),
        ("healthcare_facilities", ("opening_hours",)),
        ("disease_reports", ("notes", "source_url")),
        ("water_contamination_reports", ("escalation_reason", "escalated_at", "pin_code", "water_source")),
    ):
        inspector = sa.inspect(op.get_bind())
        if table not in inspector.get_table_names():
            continue
        existing = {item["name"] for item in inspector.get_columns(table)}
        for column in columns:
            if column in existing:
                op.drop_column(table, column)
