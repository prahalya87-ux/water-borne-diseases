"""Allow sourced reports to omit unpublished case counts."""

from alembic import op
import sqlalchemy as sa

revision = "20261027_02"
down_revision = "20261027_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "disease_reports" not in inspector.get_table_names():
        return
    columns = {column["name"]: column for column in inspector.get_columns("disease_reports")}
    cases = columns.get("cases")
    if cases and cases["nullable"] is False:
        with op.batch_alter_table("disease_reports") as batch_op:
            batch_op.alter_column("cases", existing_type=sa.Integer(), nullable=True)


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "disease_reports" not in inspector.get_table_names():
        return
    columns = {column["name"]: column for column in inspector.get_columns("disease_reports")}
    cases = columns.get("cases")
    if cases and cases["nullable"] is True:
        with op.batch_alter_table("disease_reports") as batch_op:
            batch_op.alter_column("cases", existing_type=sa.Integer(), nullable=False)
