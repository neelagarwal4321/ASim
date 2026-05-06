"""001_initial_schema

Revision ID: c5b9376eadf
Revises:
Create Date: 2026-05-06

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "c5b9376eadf"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=True),
        sa.Column("display_name", sa.String(100), nullable=True),
        sa.Column("avatar_url", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
        sa.Column("deleted_at", sa.DateTime, nullable=True),
    )

    op.create_table(
        "oauth_accounts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("provider_user_id", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )

    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("token_hash", sa.String(255), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime, nullable=False),
        sa.Column("revoked", sa.Boolean, nullable=False, default=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )

    op.create_table(
        "simulation_configs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("scenario", sa.Text, nullable=False),
        sa.Column("agent_count", sa.Integer, nullable=False, default=50),
        sa.Column("rounds", sa.Integer, nullable=False, default=5),
        sa.Column("seed", sa.Integer, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, default="pending"),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
        sa.Column("deleted_at", sa.DateTime, nullable=True),
    )

    op.create_table(
        "agent_profiles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("simulation_id", sa.String(36), sa.ForeignKey("simulation_configs.id"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("archetype", sa.String(50), nullable=False),
        sa.Column("moral_alignment", sa.String(50), nullable=False),
        sa.Column("appeal_type", sa.String(50), nullable=False),
        sa.Column("trait_vector", sa.JSON, nullable=False),
        sa.Column("core_beliefs", sa.JSON, nullable=False),
        sa.Column("voice_style", sa.Text, nullable=False),
    )

    op.create_table(
        "relationship_edges",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("simulation_id", sa.String(36), sa.ForeignKey("simulation_configs.id"), nullable=False),
        sa.Column("from_agent_id", sa.String(36), nullable=False),
        sa.Column("to_agent_id", sa.String(36), nullable=False),
        sa.Column("trust_score", sa.Float, nullable=False, default=0.5),
        sa.Column("interaction_count", sa.Integer, nullable=False, default=0),
        sa.Column("betrayed", sa.Boolean, nullable=False, default=False),
    )

    op.create_table(
        "simulation_results",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("simulation_id", sa.String(36), sa.ForeignKey("simulation_configs.id"), unique=True, nullable=False),
        sa.Column("verdict", sa.Text, nullable=False),
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column("distribution", sa.JSON, nullable=False),
        sa.Column("avg_stance", sa.Float, nullable=False),
        sa.Column("narrative", sa.Text, nullable=False),
        sa.Column("hallucination_level", sa.String(20), nullable=False, default="none"),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )

    op.create_table(
        "injected_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("simulation_id", sa.String(36), sa.ForeignKey("simulation_configs.id"), nullable=False),
        sa.Column("round_num", sa.Integer, nullable=False),
        sa.Column("event_text", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )

    op.create_table(
        "api_key_audit",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("action", sa.String(20), nullable=False),
        sa.Column("simulation_id", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("api_key_audit")
    op.drop_table("injected_events")
    op.drop_table("simulation_results")
    op.drop_table("relationship_edges")
    op.drop_table("agent_profiles")
    op.drop_table("simulation_configs")
    op.drop_table("refresh_tokens")
    op.drop_table("oauth_accounts")
    op.drop_table("users")
