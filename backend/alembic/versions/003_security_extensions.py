"""security extensions: blocked_ips, user_mfa, account lockout columns

Revision ID: 003
Revises: 002
Create Date: 2024-01-03 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # blocked_ips
    op.create_table(
        "blocked_ips",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("ip_address", sa.String(64), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("blocked_by_user_id", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["blocked_by_user_id"], ["users.id"],
            name="fk_blocked_ips_blocked_by_user_id_users", ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_blocked_ips"),
        sa.UniqueConstraint("ip_address", name="uq_blocked_ips_ip_address"),
    )
    op.create_index("ix_blocked_ips_ip_address", "blocked_ips", ["ip_address"])

    # user_mfa
    op.create_table(
        "user_mfa",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("totp_secret", sa.String(255), nullable=True),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("backup_codes", postgresql.ARRAY(sa.String(64)), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="fk_user_mfa_user_id_users", ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_user_mfa"),
        sa.UniqueConstraint("user_id", name="uq_user_mfa_user_id"),
    )

    # users: lockout columns
    op.add_column(
        "users",
        sa.Column("failed_login_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "users",
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "locked_until")
    op.drop_column("users", "failed_login_count")
    op.drop_table("user_mfa")
    op.drop_index("ix_blocked_ips_ip_address", table_name="blocked_ips")
    op.drop_table("blocked_ips")
