"""012_relationship_edge_fks

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-06-03 00:01:00.000000
"""
from alembic import op

revision = 'b2c3d4e5f6a7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    op.create_foreign_key(
        'fk_edges_from_agent', 'relationship_edges', 'agent_profiles',
        ['from_agent_id'], ['id']
    )
    op.create_foreign_key(
        'fk_edges_to_agent', 'relationship_edges', 'agent_profiles',
        ['to_agent_id'], ['id']
    )


def downgrade():
    op.drop_constraint('fk_edges_from_agent', 'relationship_edges', type_='foreignkey')
    op.drop_constraint('fk_edges_to_agent', 'relationship_edges', type_='foreignkey')
