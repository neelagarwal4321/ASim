"""005_refresh_token_family
Revision ID: f2b3c4d5e6f7
Revises: e1a2b3c4d5e6
Create Date: 2026-06-02 00:00:01.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'f2b3c4d5e6f7'
down_revision = 'e1a2b3c4d5e6'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column(
        'refresh_tokens',
        sa.Column('family_id', sa.String(36), nullable=False, server_default=sa.text("gen_random_uuid()::text"))
    )
    op.create_index('ix_refresh_tokens_family_id', 'refresh_tokens', ['family_id'])

def downgrade():
    op.drop_index('ix_refresh_tokens_family_id', 'refresh_tokens')
    op.drop_column('refresh_tokens', 'family_id')
