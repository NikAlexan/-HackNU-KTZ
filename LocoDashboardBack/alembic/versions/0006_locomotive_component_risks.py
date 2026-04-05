"""Add component_risks to locomotives

Revision ID: 0006
Revises: 0005
Create Date: 2026-04-05 00:00:00.000000
"""
import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("locomotives", sa.Column("component_risks", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("locomotives", "component_risks")
