"""Add asset_id, regime, and runtime to predictions

Revision ID: a8c4e91f2b10
Revises: 7402cafe3126
Create Date: 2026-11-26 10:35:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a8c4e91f2b10"
down_revision: Union[str, Sequence[str], None] = "7402cafe3126"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add multi-asset tracking columns and composite index to predictions."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_cols = {c["name"] for c in inspector.get_columns("predictions")}

    if "asset_id" not in existing_cols:
        op.add_column("predictions", sa.Column("asset_id", sa.String(length=64), nullable=True))
    if "regime" not in existing_cols:
        op.add_column("predictions", sa.Column("regime", sa.String(length=32), nullable=True))
    if "runtime" not in existing_cols:
        op.add_column("predictions", sa.Column("runtime", sa.String(length=32), nullable=True))

    existing_indexes = {idx["name"] for idx in inspector.get_indexes("predictions")}
    if "ix_predictions_asset_id" not in existing_indexes:
        op.create_index("ix_predictions_asset_id", "predictions", ["asset_id"], unique=False)
    if "ix_predictions_asset_ts" not in existing_indexes:
        op.create_index("ix_predictions_asset_ts", "predictions", ["asset_id", "timestamp"], unique=False)


def downgrade() -> None:
    """Remove multi-asset tracking columns from predictions."""
    op.drop_index("ix_predictions_asset_ts", table_name="predictions")
    op.drop_index("ix_predictions_asset_id", table_name="predictions")
    op.drop_column("predictions", "runtime")
    op.drop_column("predictions", "regime")
    op.drop_column("predictions", "asset_id")
