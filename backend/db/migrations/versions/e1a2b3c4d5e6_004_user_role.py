"""004_user_role
Revision ID: e1a2b3c4d5e6
Revises: 7f3a8b2c41d9
Create Date: 2026-06-02 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'e1a2b3c4d5e6'
down_revision = '7f3a8b2c41d9'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('users', sa.Column('role', sa.String(20), nullable=False, server_default='free'))

def downgrade():
    op.drop_column('users', 'role')
