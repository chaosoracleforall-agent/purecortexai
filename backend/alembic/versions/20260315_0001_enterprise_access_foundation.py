"""Create enterprise developer access foundation tables.

Revision ID: 20260315_0001
Revises:
Create Date: 2026-03-15 00:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260315_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "developer_access_requests",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("requester_name", sa.String(length=255), nullable=False),
        sa.Column("requester_email", sa.String(length=320), nullable=False),
        sa.Column("organization", sa.String(length=255), nullable=True),
        sa.Column("use_case", sa.Text(), nullable=False),
        sa.Column("requested_surfaces", sa.JSON(), nullable=False),
        sa.Column("requested_access_level", sa.String(length=32), nullable=False),
        sa.Column("requested_ips", sa.JSON(), nullable=False),
        sa.Column("expected_rpm", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by", sa.String(length=320), nullable=True),
        sa.Column("issued_key_id", sa.String(length=36), nullable=True),
    )
    op.create_index(
        "ix_developer_access_requests_requester_email",
        "developer_access_requests",
        ["requester_email"],
    )
    op.create_index(
        "ix_developer_access_requests_status",
        "developer_access_requests",
        ["status"],
    )

    op.create_table(
        "api_keys",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("key_id", sa.String(length=32), nullable=False),
        sa.Column("key_prefix", sa.String(length=64), nullable=False),
        sa.Column("secret_hash", sa.String(length=255), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=True),
        sa.Column("owner_name", sa.String(length=255), nullable=False),
        sa.Column("owner_email", sa.String(length=320), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("access_level", sa.String(length=32), nullable=False),
        sa.Column("scopes", sa.JSON(), nullable=False),
        sa.Column("intended_surfaces", sa.JSON(), nullable=False),
        sa.Column("rate_limit_profile", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(length=320), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_by", sa.String(length=320), nullable=True),
        sa.Column("revocation_reason", sa.Text(), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_ip", sa.String(length=64), nullable=True),
        sa.Column("override_no_ip_allowlist", sa.Boolean(), nullable=False),
        sa.Column("override_reason", sa.Text(), nullable=True),
        sa.Column("request_id", sa.String(length=36), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["request_id"], ["developer_access_requests.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_api_keys_key_id", "api_keys", ["key_id"], unique=True)
    op.create_index("ix_api_keys_owner_email", "api_keys", ["owner_email"])
    op.create_index("ix_api_keys_status", "api_keys", ["status"])

    op.create_foreign_key(
        "fk_developer_access_requests_issued_key_id_api_keys",
        "developer_access_requests",
        "api_keys",
        ["issued_key_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "api_key_ip_allowlists",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("api_key_id", sa.String(length=36), nullable=False),
        sa.Column("cidr", sa.String(length=64), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(length=320), nullable=True),
        sa.ForeignKeyConstraint(["api_key_id"], ["api_keys.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_api_key_ip_allowlists_api_key_id",
        "api_key_ip_allowlists",
        ["api_key_id"],
    )

    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("actor_type", sa.String(length=64), nullable=False),
        sa.Column("actor_email", sa.String(length=320), nullable=True),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("target_type", sa.String(length=64), nullable=False),
        sa.Column("target_id", sa.String(length=64), nullable=True),
        sa.Column("request_ip", sa.String(length=64), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_events_actor_email", "audit_events", ["actor_email"])
    op.create_index("ix_audit_events_event_type", "audit_events", ["event_type"])
    op.create_index("ix_audit_events_target_id", "audit_events", ["target_id"])


def downgrade() -> None:
    op.drop_index("ix_audit_events_target_id", table_name="audit_events")
    op.drop_index("ix_audit_events_event_type", table_name="audit_events")
    op.drop_index("ix_audit_events_actor_email", table_name="audit_events")
    op.drop_table("audit_events")

    op.drop_index("ix_api_key_ip_allowlists_api_key_id", table_name="api_key_ip_allowlists")
    op.drop_table("api_key_ip_allowlists")

    op.drop_constraint(
        "fk_developer_access_requests_issued_key_id_api_keys",
        "developer_access_requests",
        type_="foreignkey",
    )
    op.drop_index("ix_api_keys_status", table_name="api_keys")
    op.drop_index("ix_api_keys_owner_email", table_name="api_keys")
    op.drop_index("ix_api_keys_key_id", table_name="api_keys")
    op.drop_table("api_keys")

    op.drop_index(
        "ix_developer_access_requests_status",
        table_name="developer_access_requests",
    )
    op.drop_index(
        "ix_developer_access_requests_requester_email",
        table_name="developer_access_requests",
    )
    op.drop_table("developer_access_requests")
