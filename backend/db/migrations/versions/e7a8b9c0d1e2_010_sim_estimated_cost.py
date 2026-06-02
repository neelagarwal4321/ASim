"""010_sim_estimated_cost
Revision ID: e7a8b9c0d1e2
Revises: d6f7a8b9c0d1
Create Date: 2026-06-02 00:00:06.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'e7a8b9c0d1e2'
down_revision = 'd6f7a8b9c0d1'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('simulation_configs', sa.Column('estimated_cost', sa.Numeric(10, 4), nullable=True))

def downgrade():
    op.drop_column('simulation_configs', 'estimated_cost')
