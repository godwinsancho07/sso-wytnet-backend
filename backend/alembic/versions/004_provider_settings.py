"""provider_settings table for runtime social provider config

Revision ID: 004
Revises: 003
Create Date: 2024-01-04 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "provider_settings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("client_id", sa.String(255), nullable=True),
        sa.Column("client_secret_encrypted", sa.String(1024), nullable=True),
        sa.Column("redirect_uri", sa.String(512), nullable=True),
        sa.Column("extra_config", sa.JSON(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("updated_by_user_id", sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(
            ["updated_by_user_id"],
            ["users.id"],
            name="fk_provider_settings_updated_by_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_provider_settings"),
        sa.UniqueConstraint("provider", name="uq_provider_settings_provider"),
    )
    op.create_index(
        "ix_provider_settings_provider", "provider_settings", ["provider"]
    )


def downgrade() -> None:
    op.drop_index("ix_provider_settings_provider", table_name="provider_settings")
    op.drop_table("provider_settings")
