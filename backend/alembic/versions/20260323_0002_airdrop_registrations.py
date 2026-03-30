"""Create airdrop registrations table.

Revision ID: 20260323_0002
Revises: 20260315_0001
Create Date: 2026-03-23 00:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260323_0002"
down_revision = "20260315_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "airdrop_registrations",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("wallet_address", sa.String(length=64), nullable=False),
        sa.Column("source_ip", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_airdrop_registrations_wallet_address",
        "airdrop_registrations",
        ["wallet_address"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_airdrop_registrations_wallet_address",
        table_name="airdrop_registrations",
    )
    op.drop_table("airdrop_registrations")
