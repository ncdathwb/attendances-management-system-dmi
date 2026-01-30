"""Add minutes columns to attendance table

Revision ID: f1a2b3c4d5e6
Revises: ea266e08c453
Create Date: 2026-01-22 09:10:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f1a2b3c4d5e6'
down_revision = ('d35f9be003ab', 'e3e23f6a4929')  # Merge multiple heads
branch_labels = None
depends_on = None


def upgrade():
    """Add integer minutes columns to attendance table for precision"""
    # Add new integer minutes columns
    # These replace float hours columns to eliminate floating point errors
    
    # Break time in minutes (default 60 = 1 hour)
    op.add_column('attendances', sa.Column('break_time_minutes', sa.Integer(), nullable=False, server_default='60'))
    
    # Total work time in minutes
    op.add_column('attendances', sa.Column('total_work_minutes', sa.Integer(), nullable=True))
    
    # Regular work hours in minutes
    op.add_column('attendances', sa.Column('regular_work_minutes', sa.Integer(), nullable=True))
    
    # Required work hours in minutes (default 480 = 8 hours)
    op.add_column('attendances', sa.Column('required_minutes', sa.Integer(), nullable=True, server_default='480'))
    
    # Comp time columns in minutes
    op.add_column('attendances', sa.Column('comp_time_regular_minutes', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('attendances', sa.Column('comp_time_overtime_minutes', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('attendances', sa.Column('comp_time_ot_before_22_minutes', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('attendances', sa.Column('comp_time_ot_after_22_minutes', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('attendances', sa.Column('overtime_comp_time_minutes', sa.Integer(), nullable=False, server_default='0'))


def downgrade():
    """Remove minutes columns (rollback migration)"""
    op.drop_column('attendances', 'overtime_comp_time_minutes')
    op.drop_column('attendances', 'comp_time_ot_after_22_minutes')
    op.drop_column('attendances', 'comp_time_ot_before_22_minutes')
    op.drop_column('attendances', 'comp_time_overtime_minutes')
    op.drop_column('attendances', 'comp_time_regular_minutes')
    op.drop_column('attendances', 'required_minutes')
    op.drop_column('attendances', 'regular_work_minutes')
    op.drop_column('attendances', 'total_work_minutes')
    op.drop_column('attendances', 'break_time_minutes')
