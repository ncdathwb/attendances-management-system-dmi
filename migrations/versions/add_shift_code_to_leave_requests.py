"""Add shift_code to leave_requests table

Revision ID: add_shift_code_to_leave_requests
Revises: ea266e08c453
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_shift_code_to_leave_requests'
down_revision = 'ea266e08c453'
branch_labels = None
depends_on = None


def upgrade():
    """Add shift_code column to leave_requests table"""
    # Add shift_code column to leave_requests table
    op.add_column('leave_requests', sa.Column('shift_code', sa.String(10), nullable=True))


def downgrade():
    """Remove shift_code column from leave_requests table"""
    # Remove shift_code column from leave_requests table
    op.drop_column('leave_requests', 'shift_code')
