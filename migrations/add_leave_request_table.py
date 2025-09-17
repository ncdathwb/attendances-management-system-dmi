"""
Migration script to add leave_requests table
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_leave_request_table'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Create leave_requests table
    op.create_table('leave_requests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('employee_name', sa.String(length=100), nullable=False),
        sa.Column('team', sa.String(length=50), nullable=False),
        sa.Column('employee_code', sa.String(length=20), nullable=False),
        sa.Column('reason_sick_child', sa.Boolean(), default=False),
        sa.Column('reason_sick', sa.Boolean(), default=False),
        sa.Column('reason_death_anniversary', sa.Boolean(), default=False),
        sa.Column('reason_other', sa.Boolean(), default=False),
        sa.Column('reason_other_detail', sa.Text(), nullable=True),
        sa.Column('hospital_confirmation', sa.Boolean(), default=False),
        sa.Column('wedding_invitation', sa.Boolean(), default=False),
        sa.Column('death_birth_certificate', sa.Boolean(), default=False),
        sa.Column('leave_from_hour', sa.Integer(), nullable=False),
        sa.Column('leave_from_minute', sa.Integer(), nullable=False),
        sa.Column('leave_from_day', sa.Integer(), nullable=False),
        sa.Column('leave_from_month', sa.Integer(), nullable=False),
        sa.Column('leave_from_year', sa.Integer(), nullable=False),
        sa.Column('leave_to_hour', sa.Integer(), nullable=False),
        sa.Column('leave_to_minute', sa.Integer(), nullable=False),
        sa.Column('leave_to_day', sa.Integer(), nullable=False),
        sa.Column('leave_to_month', sa.Integer(), nullable=False),
        sa.Column('leave_to_year', sa.Integer(), nullable=False),
        sa.Column('annual_leave_days', sa.Integer(), default=0),
        sa.Column('unpaid_leave_days', sa.Integer(), default=0),
        sa.Column('special_leave_days', sa.Integer(), default=0),
        sa.Column('special_leave_type', sa.String(length=50), nullable=True),
        sa.Column('substitute_name', sa.String(length=100), nullable=True),
        sa.Column('substitute_employee_id', sa.String(length=20), nullable=True),
        sa.Column('status', sa.String(length=20), default='pending'),
        sa.Column('manager_approval', sa.Boolean(), default=False),
        sa.Column('manager_signature', sa.Text(), nullable=True),
        sa.Column('manager_signer_id', sa.Integer(), nullable=True),
        sa.Column('direct_superior_approval', sa.Boolean(), default=False),
        sa.Column('direct_superior_type', sa.String(length=20), nullable=True),
        sa.Column('direct_superior_signature', sa.Text(), nullable=True),
        sa.Column('direct_superior_signer_id', sa.Integer(), nullable=True),
        sa.Column('applicant_signature', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['manager_signer_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['direct_superior_signer_id'], ['users.id'], )
    )

def downgrade():
    # Drop leave_requests table
    op.drop_table('leave_requests')
