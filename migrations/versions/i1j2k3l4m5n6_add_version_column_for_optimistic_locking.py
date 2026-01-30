"""Add version column for optimistic locking (B3 fix)

Revision ID: i1j2k3l4m5n6
Revises: h1i2j3k4l5m6
Create Date: 2026-01-28 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'i1j2k3l4m5n6'
down_revision = 'h1i2j3k4l5m6'
branch_labels = None
depends_on = None


def upgrade():
    """Add version column for optimistic locking in approval workflow (B3 fix)"""
    with op.batch_alter_table('attendances', schema=None) as batch_op:
        batch_op.add_column(sa.Column('version', sa.Integer(), nullable=False, server_default='1'))


def downgrade():
    """Remove version column"""
    with op.batch_alter_table('attendances', schema=None) as batch_op:
        batch_op.drop_column('version')
