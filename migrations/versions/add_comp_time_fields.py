"""add comp time fields

Revision ID: add_comp_time_fields
Revises: ea266e08c453
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_comp_time_fields'
down_revision = 'ea266e08c453'
branch_labels = None
depends_on = None


def upgrade():
    # Thêm 2 trường mới cho giờ đối ứng
    op.add_column('attendances', sa.Column('comp_time_regular', sa.Float(), nullable=False, server_default='0.0'))
    op.add_column('attendances', sa.Column('comp_time_overtime', sa.Float(), nullable=False, server_default='0.0'))
    
    # Cập nhật dữ liệu cũ: chuyển overtime_comp_time thành comp_time_overtime
    op.execute("""
        UPDATE attendances 
        SET comp_time_overtime = overtime_comp_time 
        WHERE overtime_comp_time IS NOT NULL AND overtime_comp_time > 0
    """)


def downgrade():
    # Xóa 2 trường mới
    op.drop_column('attendances', 'comp_time_overtime')
    op.drop_column('attendances', 'comp_time_regular')
