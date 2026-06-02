"""006_sim_retry_count
Revision ID: a3c4d5e6f7a8
Revises: f2b3c4d5e6f7
Create Date: 2026-06-02 00:00:02.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'a3c4d5e6f7a8'
down_revision = 'f2b3c4d5e6f7'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('simulation_configs', sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'))

def downgrade():
    op.drop_column('simulation_configs', 'retry_count')
