"""Add component_risks_json to generated_readings

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-05 00:00:00.000000
"""
import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "generated_readings",
        sa.Column("component_risks_json", sa.JSON(), nullable=True),
    )
    op.execute("UPDATE generated_readings SET component_risks_json = '{}'")
    op.alter_column("generated_readings", "component_risks_json", nullable=False)


def downgrade() -> None:
    op.drop_column("generated_readings", "component_risks_json")
