"""merge multiple heads

Revision ID: a27061361835
Revises: 5b8f1c2e7a3a, 8bc366d36e2e, add_comp_time_fields
Create Date: 2025-08-12 15:02:40.917997

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a27061361835'
down_revision = ('5b8f1c2e7a3a', '8bc366d36e2e', 'add_comp_time_fields')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
