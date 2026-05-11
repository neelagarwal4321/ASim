"""003_report_columns

Adds counterfactuals + report JSON columns to simulation_results so the
counterfactual_prober and report_assembler outputs persist alongside the
verdict and narrative.

Revision ID: 7f3a8b2c41d9
Revises: a1c96f55dc97
Create Date: 2026-05-11 19:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '7f3a8b2c41d9'
down_revision: Union[str, None] = 'a1c96f55dc97'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'simulation_results',
        sa.Column('counterfactuals', sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
    )
    op.add_column(
        'simulation_results',
        sa.Column('report', sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
    )


def downgrade() -> None:
    op.drop_column('simulation_results', 'report')
    op.drop_column('simulation_results', 'counterfactuals')
