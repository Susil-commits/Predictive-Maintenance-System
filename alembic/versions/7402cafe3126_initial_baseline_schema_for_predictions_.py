"""Initial baseline schema for predictions and users

Revision ID: 7402cafe3126
Revises: 
Create Date: 2026-09-05 16:33:37.709788

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7402cafe3126'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - create predictions and pms_users tables if not present."""
    # pms_users table
    op.create_table(
        'pms_users',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('username', sa.String(length=64), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=32), nullable=False, server_default='employee'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        if_not_exists=True
    )
    try:
        op.create_index('ix_pms_users_username', 'pms_users', ['username'], unique=True, if_not_exists=True)
    except Exception:
        pass

    # predictions table
    op.create_table(
        'predictions',
        sa.Column('prediction_id', sa.String(length=64), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.Column('temperature', sa.Float(), nullable=False),
        sa.Column('rpm', sa.Float(), nullable=False),
        sa.Column('pressure', sa.Float(), nullable=False),
        sa.Column('vibration', sa.Float(), nullable=False),
        sa.Column('operating_hours', sa.Float(), nullable=False),
        sa.Column('failure_risk', sa.String(length=16), nullable=False),
        sa.Column('probability', sa.Float(), nullable=False),
        sa.Column('maintenance_required', sa.Boolean(), nullable=False),
        sa.Column('shap_values', sa.JSON(), nullable=True),
        sa.Column('contributing_factors', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('prediction_id'),
        if_not_exists=True
    )
    try:
        op.create_index('ix_predictions_prediction_id', 'predictions', ['prediction_id'], unique=False, if_not_exists=True)
        op.create_index('ix_predictions_timestamp', 'predictions', ['timestamp'], unique=False, if_not_exists=True)
    except Exception:
        pass


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('predictions')
    op.drop_table('pms_users')
