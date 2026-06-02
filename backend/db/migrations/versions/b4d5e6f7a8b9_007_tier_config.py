"""007_tier_config
Revision ID: b4d5e6f7a8b9
Revises: a3c4d5e6f7a8
Create Date: 2026-06-02 00:00:03.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'b4d5e6f7a8b9'
down_revision = 'a3c4d5e6f7a8'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'tier_config',
        sa.Column('role', sa.String(20), primary_key=True),
        sa.Column('max_agents', sa.Integer(), nullable=False),
        sa.Column('max_rounds', sa.Integer(), nullable=False),
        sa.Column('max_daily_sims', sa.Integer(), nullable=False),
        sa.Column('max_concurrent', sa.Integer(), nullable=False),
        sa.Column('max_duration_seconds', sa.Integer(), nullable=False),
    )
    op.execute("""
        INSERT INTO tier_config VALUES
        ('free',  50,  10,  10,   1, 1800),
        ('pro',  200,  50, 100,   3, 7200),
        ('admin', 500, 200, 9999, 99, 7200)
    """)

def downgrade():
    op.drop_table('tier_config')
