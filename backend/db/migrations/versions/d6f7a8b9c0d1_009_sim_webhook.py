"""009_sim_webhook
Revision ID: d6f7a8b9c0d1
Revises: c5e6f7a8b9c0
Create Date: 2026-06-02 00:00:05.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'd6f7a8b9c0d1'
down_revision = 'c5e6f7a8b9c0'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('simulation_configs', sa.Column('webhook_url', sa.Text(), nullable=True))

def downgrade():
    op.drop_column('simulation_configs', 'webhook_url')
