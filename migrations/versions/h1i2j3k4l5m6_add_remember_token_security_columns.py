"""Add remember token security columns (IP and User-Agent binding)

Revision ID: h1i2j3k4l5m6
Revises: g1h2i3j4k5l6
Create Date: 2026-01-28 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'h1i2j3k4l5m6'
down_revision = 'g1h2i3j4k5l6'
branch_labels = None
depends_on = None


def upgrade():
    """Add IP and User-Agent columns for remember token security (B4 fix)"""
    # Add remember_token_ip column
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('remember_token_ip', sa.String(length=45), nullable=True))
        batch_op.add_column(sa.Column('remember_token_user_agent', sa.String(length=255), nullable=True))

    # Add unique constraint for attendance (B1 fix) - may fail if duplicates exist
    try:
        with op.batch_alter_table('attendances', schema=None) as batch_op:
            batch_op.create_unique_constraint('uq_attendance_user_date', ['user_id', 'date'])
    except Exception as e:
        print(f"Warning: Could not create unique constraint (duplicates may exist): {e}")


def downgrade():
    """Remove IP and User-Agent columns"""
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('remember_token_user_agent')
        batch_op.drop_column('remember_token_ip')

    try:
        with op.batch_alter_table('attendances', schema=None) as batch_op:
            batch_op.drop_constraint('uq_attendance_user_date', type_='unique')
    except Exception:
        pass
