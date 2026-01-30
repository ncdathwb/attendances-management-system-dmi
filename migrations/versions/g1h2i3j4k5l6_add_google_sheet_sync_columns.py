"""add google sheet sync columns to leave_requests

Revision ID: g1h2i3j4k5l6
Revises: f1a2b3c4d5e6
Create Date: 2026-01-28 10:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'g1h2i3j4k5l6'
down_revision = 'f1a2b3c4d5e6'
branch_labels = None
depends_on = None


def upgrade():
    # Thêm các cột theo dõi đồng bộ Google Sheet vào bảng leave_requests
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)

    # Kiểm tra xem bảng leave_requests có tồn tại không
    tables = inspector.get_table_names()
    if 'leave_requests' not in tables:
        return

    # Lấy danh sách cột hiện tại
    columns = [col['name'] for col in inspector.get_columns('leave_requests')]

    # Thêm cột google_sheet_synced nếu chưa có
    if 'google_sheet_synced' not in columns:
        op.add_column('leave_requests',
            sa.Column('google_sheet_synced', sa.Boolean(), nullable=True, server_default='0'))

    # Thêm cột google_sheet_sync_at nếu chưa có
    if 'google_sheet_sync_at' not in columns:
        op.add_column('leave_requests',
            sa.Column('google_sheet_sync_at', sa.DateTime(), nullable=True))

    # Thêm cột google_sheet_sync_error nếu chưa có
    if 'google_sheet_sync_error' not in columns:
        op.add_column('leave_requests',
            sa.Column('google_sheet_sync_error', sa.Text(), nullable=True))

    # Thêm cột google_sheet_sync_attempts nếu chưa có
    if 'google_sheet_sync_attempts' not in columns:
        op.add_column('leave_requests',
            sa.Column('google_sheet_sync_attempts', sa.Integer(), nullable=True, server_default='0'))


def downgrade():
    # Xóa các cột khi rollback
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)

    tables = inspector.get_table_names()
    if 'leave_requests' not in tables:
        return

    columns = [col['name'] for col in inspector.get_columns('leave_requests')]

    if 'google_sheet_sync_attempts' in columns:
        op.drop_column('leave_requests', 'google_sheet_sync_attempts')

    if 'google_sheet_sync_error' in columns:
        op.drop_column('leave_requests', 'google_sheet_sync_error')

    if 'google_sheet_sync_at' in columns:
        op.drop_column('leave_requests', 'google_sheet_sync_at')

    if 'google_sheet_synced' in columns:
        op.drop_column('leave_requests', 'google_sheet_synced')
