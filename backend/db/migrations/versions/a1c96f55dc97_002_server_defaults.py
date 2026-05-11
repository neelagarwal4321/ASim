"""002_server_defaults

Revision ID: a1c96f55dc97
Revises: c5b9376eadf
Create Date: 2026-05-07 19:01:51.215174

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a1c96f55dc97'
down_revision: Union[str, None] = 'c5b9376eadf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_UUID_DEFAULT = sa.text("gen_random_uuid()::varchar")
_NOW = sa.text("now()")


def upgrade() -> None:
    # users — Node INSERT omits id, created_at, updated_at
    op.alter_column('users', 'id', server_default=_UUID_DEFAULT)
    op.alter_column('users', 'created_at', server_default=_NOW)
    op.alter_column('users', 'updated_at', server_default=_NOW)

    # refresh_tokens — Node INSERT omits id, created_at
    op.alter_column('refresh_tokens', 'id', server_default=_UUID_DEFAULT)
    op.alter_column('refresh_tokens', 'created_at', server_default=_NOW)

    # simulation_configs — Node INSERT omits created_at, updated_at (id provided)
    op.alter_column('simulation_configs', 'created_at', server_default=_NOW)
    op.alter_column('simulation_configs', 'updated_at', server_default=_NOW)

    # remaining tables — written by Python ORM, but add defaults for consistency
    op.alter_column('oauth_accounts', 'id', server_default=_UUID_DEFAULT)
    op.alter_column('oauth_accounts', 'created_at', server_default=_NOW)

    op.alter_column('simulation_results', 'id', server_default=_UUID_DEFAULT)
    op.alter_column('simulation_results', 'created_at', server_default=_NOW)

    op.alter_column('relationship_edges', 'id', server_default=_UUID_DEFAULT)

    op.alter_column('injected_events', 'id', server_default=_UUID_DEFAULT)
    op.alter_column('injected_events', 'created_at', server_default=_NOW)

    op.alter_column('api_key_audit', 'id', server_default=_UUID_DEFAULT)
    op.alter_column('api_key_audit', 'created_at', server_default=_NOW)


def downgrade() -> None:
    op.alter_column('api_key_audit', 'created_at', server_default=None)
    op.alter_column('api_key_audit', 'id', server_default=None)

    op.alter_column('injected_events', 'created_at', server_default=None)
    op.alter_column('injected_events', 'id', server_default=None)

    op.alter_column('relationship_edges', 'id', server_default=None)

    op.alter_column('simulation_results', 'created_at', server_default=None)
    op.alter_column('simulation_results', 'id', server_default=None)

    op.alter_column('oauth_accounts', 'created_at', server_default=None)
    op.alter_column('oauth_accounts', 'id', server_default=None)

    op.alter_column('simulation_configs', 'updated_at', server_default=None)
    op.alter_column('simulation_configs', 'created_at', server_default=None)

    op.alter_column('refresh_tokens', 'created_at', server_default=None)
    op.alter_column('refresh_tokens', 'id', server_default=None)

    op.alter_column('users', 'updated_at', server_default=None)
    op.alter_column('users', 'created_at', server_default=None)
    op.alter_column('users', 'id', server_default=None)
