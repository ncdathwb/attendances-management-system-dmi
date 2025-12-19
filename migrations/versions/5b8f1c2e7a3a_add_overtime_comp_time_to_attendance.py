"""add overtime_comp_time to Attendance

Revision ID: 5b8f1c2e7a3a
Revises: 23929aa3dfe0
Create Date: 2025-08-12 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5b8f1c2e7a3a'
down_revision = '23929aa3dfe0'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('attendances', schema=None) as batch_op:
        batch_op.add_column(sa.Column('overtime_comp_time', sa.Float(), nullable=False, server_default='0'))


def downgrade():
    with op.batch_alter_table('attendances', schema=None) as batch_op:
        batch_op.drop_column('overtime_comp_time')


