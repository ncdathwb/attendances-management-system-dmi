"""Add excluded days columns to leave_request table

Revision ID: j1k2l3m4n5o6
Revises: i1j2k3l4m5n6
Create Date: 2026-01-30 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'j1k2l3m4n5o6'
down_revision = 'i1j2k3l4m5n6'
branch_labels = None
depends_on = None


def upgrade():
    """Add excluded days columns for tracking weekends and holidays in leave requests"""
    with op.batch_alter_table('leave_requests', schema=None) as batch_op:
        batch_op.add_column(sa.Column('excluded_days_json', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('total_calendar_days', sa.Integer(), nullable=True, server_default='0'))
        batch_op.add_column(sa.Column('total_excluded_days', sa.Integer(), nullable=True, server_default='0'))
        batch_op.add_column(sa.Column('total_working_days', sa.Float(), nullable=True, server_default='0'))
        batch_op.add_column(sa.Column('weekend_count', sa.Integer(), nullable=True, server_default='0'))
        batch_op.add_column(sa.Column('vietnamese_holiday_count', sa.Integer(), nullable=True, server_default='0'))
        batch_op.add_column(sa.Column('japanese_holiday_count', sa.Integer(), nullable=True, server_default='0'))


def downgrade():
    """Remove excluded days columns"""
    with op.batch_alter_table('leave_requests', schema=None) as batch_op:
        batch_op.drop_column('japanese_holiday_count')
        batch_op.drop_column('vietnamese_holiday_count')
        batch_op.drop_column('weekend_count')
        batch_op.drop_column('total_working_days')
        batch_op.drop_column('total_excluded_days')
        batch_op.drop_column('total_calendar_days')
        batch_op.drop_column('excluded_days_json')
