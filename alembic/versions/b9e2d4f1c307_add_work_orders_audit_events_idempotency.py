"""Add work_orders, audit_events, and idempotency_keys tables

Revision ID: b9e2d4f1c307
Revises: a8c4e91f2b10
Create Date: 2026-11-26 10:45:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b9e2d4f1c307"
down_revision: Union[str, Sequence[str], None] = "a8c4e91f2b10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create persistent CMMS work_orders, cryptographic audit_events, and idempotency_keys tables."""
    op.create_table(
        "work_orders",
        sa.Column("work_order_id", sa.String(length=64), nullable=False),
        sa.Column("prediction_id", sa.String(length=64), nullable=True),
        sa.Column("asset_id", sa.String(length=64), nullable=False),
        sa.Column("line_id", sa.String(length=128), nullable=False),
        sa.Column("plant_location", sa.String(length=128), nullable=True),
        sa.Column("failure_mode", sa.String(length=128), nullable=False),
        sa.Column("priority", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("cmms_target", sa.String(length=128), nullable=False),
        sa.Column("technician_qualification", sa.String(length=128), nullable=False),
        sa.Column("required_bom_parts", sa.JSON(), nullable=False),
        sa.Column("safety_interlocks", sa.JSON(), nullable=False),
        sa.Column("torque_specs_nm", sa.Float(), nullable=False),
        sa.Column("estimated_duration_hours", sa.Float(), nullable=False),
        sa.Column("notes", sa.String(length=1024), nullable=True),
        sa.Column("resolution_notes", sa.String(length=1024), nullable=True),
        sa.Column("actual_failure_confirmed", sa.Boolean(), nullable=True),
        sa.Column("dispatched_at", sa.DateTime(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("work_order_id"),
        if_not_exists=True,
    )
    op.create_index("ix_work_orders_asset_status", "work_orders", ["asset_id", "status"], unique=False)
    op.create_index("ix_work_orders_dispatched_at", "work_orders", ["dispatched_at"], unique=False)

    op.create_table(
        "audit_events",
        sa.Column("event_index", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("timestamp", sa.Float(), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("actor_id", sa.String(length=128), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("prev_hash", sa.String(length=64), nullable=False),
        sa.Column("event_hash", sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint("event_index"),
        if_not_exists=True,
    )
    op.create_index("ix_audit_events_timestamp", "audit_events", ["timestamp"], unique=False)
    op.create_index("ix_audit_events_event_type", "audit_events", ["event_type"], unique=False)

    op.create_table(
        "idempotency_keys",
        sa.Column("key", sa.String(length=255), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.Float(), nullable=False),
        sa.Column("expires_at", sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint("key"),
        if_not_exists=True,
    )
    op.create_index("ix_idempotency_keys_expires_at", "idempotency_keys", ["expires_at"], unique=False)


def downgrade() -> None:
    """Drop work_orders, audit_events, and idempotency_keys tables."""
    op.drop_index("ix_idempotency_keys_expires_at", table_name="idempotency_keys")
    op.drop_table("idempotency_keys")
    op.drop_index("ix_audit_events_event_type", table_name="audit_events")
    op.drop_index("ix_audit_events_timestamp", table_name="audit_events")
    op.drop_table("audit_events")
    op.drop_index("ix_work_orders_dispatched_at", table_name="work_orders")
    op.drop_index("ix_work_orders_asset_status", table_name="work_orders")
    op.drop_table("work_orders")
