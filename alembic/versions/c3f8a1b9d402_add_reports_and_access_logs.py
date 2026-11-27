"""Add diagnostic_reports and user_access_logs tables

Revision ID: c3f8a1b9d402
Revises: b9e2d4f1c307
Create Date: 2026-11-27 09:50:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3f8a1b9d402"
down_revision: Union[str, Sequence[str], None] = "b9e2d4f1c307"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create diagnostic_reports and user_access_logs tables."""
    op.create_table(
        "diagnostic_reports",
        sa.Column("report_id", sa.String(length=64), nullable=False),
        sa.Column("prediction_id", sa.String(length=64), nullable=True),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("user_name", sa.String(length=128), nullable=False),
        sa.Column("user_designation", sa.String(length=128), nullable=True),
        sa.Column("risk", sa.String(length=16), nullable=False),
        sa.Column("probability", sa.Float(), nullable=True),
        sa.Column("input_data", sa.JSON(), nullable=False),
        sa.Column("shap_factors", sa.JSON(), nullable=False),
        sa.Column("cloudinary_url", sa.String(length=512), nullable=True),
        sa.Column("saved_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("report_id"),
        if_not_exists=True,
    )
    op.create_index("ix_diagnostic_reports_user_saved", "diagnostic_reports", ["user_id", "saved_at"], unique=False)
    op.create_index("ix_diagnostic_reports_saved_at", "diagnostic_reports", ["saved_at"], unique=False)

    op.create_table(
        "user_access_logs",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("designation", sa.String(length=128), nullable=True),
        sa.Column("page", sa.String(length=64), nullable=False),
        sa.Column("accessed_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        if_not_exists=True,
    )
    op.create_index("ix_user_access_logs_user_ts", "user_access_logs", ["user_id", "accessed_at"], unique=False)
    op.create_index("ix_user_access_logs_accessed_at", "user_access_logs", ["accessed_at"], unique=False)


def downgrade() -> None:
    """Drop diagnostic_reports and user_access_logs tables."""
    op.drop_index("ix_user_access_logs_accessed_at", table_name="user_access_logs")
    op.drop_index("ix_user_access_logs_user_ts", table_name="user_access_logs")
    op.drop_table("user_access_logs")
    op.drop_index("ix_diagnostic_reports_saved_at", table_name="diagnostic_reports")
    op.drop_index("ix_diagnostic_reports_user_saved", table_name="diagnostic_reports")
    op.drop_table("diagnostic_reports")
