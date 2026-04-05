"""add users table

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-05 00:00:00.000000
"""
import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column("username", sa.String(64), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(256), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("users")
