"""008_metrics_rollup
Revision ID: c5e6f7a8b9c0
Revises: b4d5e6f7a8b9
Create Date: 2026-06-02 00:00:04.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'c5e6f7a8b9c0'
down_revision = 'b4d5e6f7a8b9'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'metrics_rollup',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('date', sa.Date(), nullable=False, unique=True),
        sa.Column('total_sims', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('verdict_distribution', sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column('avg_rounds', sa.Float(), nullable=True),
        sa.Column('provider_usage', sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
    )

def downgrade():
    op.drop_table('metrics_rollup')
