"""011_performance_indexes

Add indexes on frequently queried columns to improve query performance.

Revision ID: a1b2c3d4e5f6
Revises: e7a8b9c0d1e2
Create Date: 2026-06-03 00:00:00.000000
"""
from alembic import op

revision = 'a1b2c3d4e5f6'
down_revision = 'e7a8b9c0d1e2'
branch_labels = None
depends_on = None


def upgrade():
    # simulation_configs — most queried table
    op.create_index('ix_simulation_configs_user_id', 'simulation_configs', ['user_id'])
    op.create_index('ix_simulation_configs_status', 'simulation_configs', ['status'])
    op.create_index('ix_simulation_configs_user_status', 'simulation_configs', ['user_id', 'status'])
    op.create_index('ix_simulation_configs_updated_at', 'simulation_configs', ['updated_at'])

    # simulation_results — joined on every report fetch
    op.create_index('ix_simulation_results_simulation_id', 'simulation_results', ['simulation_id'])

    # agent_profiles — queried per simulation
    op.create_index('ix_agent_profiles_simulation_id', 'agent_profiles', ['simulation_id'])

    # relationship_edges — queried per simulation
    op.create_index('ix_relationship_edges_simulation_id', 'relationship_edges', ['simulation_id'])

    # injected_events — queried per simulation + round
    op.create_index('ix_injected_events_simulation_id', 'injected_events', ['simulation_id'])

    # refresh_tokens — queried on every token refresh (token_hash already unique-indexed by PK logic)
    op.create_index('ix_refresh_tokens_user_id', 'refresh_tokens', ['user_id'])
    op.create_index('ix_refresh_tokens_expires_at', 'refresh_tokens', ['expires_at'])

    # api_key_audit — queried by user
    op.create_index('ix_api_key_audit_user_id', 'api_key_audit', ['user_id'])

    # users — email lookup
    # Note: unique constraint on email already creates an index, skip


def downgrade():
    op.drop_index('ix_simulation_configs_user_id', 'simulation_configs')
    op.drop_index('ix_simulation_configs_status', 'simulation_configs')
    op.drop_index('ix_simulation_configs_user_status', 'simulation_configs')
    op.drop_index('ix_simulation_configs_updated_at', 'simulation_configs')
    op.drop_index('ix_simulation_results_simulation_id', 'simulation_results')
    op.drop_index('ix_agent_profiles_simulation_id', 'agent_profiles')
    op.drop_index('ix_relationship_edges_simulation_id', 'relationship_edges')
    op.drop_index('ix_injected_events_simulation_id', 'injected_events')
    op.drop_index('ix_refresh_tokens_user_id', 'refresh_tokens')
    op.drop_index('ix_refresh_tokens_expires_at', 'refresh_tokens')
    op.drop_index('ix_api_key_audit_user_id', 'api_key_audit')
