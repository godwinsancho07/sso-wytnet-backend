"""client_admins table for app admin scoping

Revision ID: 002
Revises: 001
Create Date: 2024-01-02 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "client_admins",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("client_id", sa.String(36), nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_client_admins_user_id_users", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["client_id"], ["oauth_clients.id"], name="fk_client_admins_client_id_oauth_clients", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_client_admins"),
        sa.UniqueConstraint("user_id", "client_id", name="uq_client_admin"),
    )
    op.create_index("ix_client_admins_user_id", "client_admins", ["user_id"])
    op.create_index("ix_client_admins_client_id", "client_admins", ["client_id"])


def downgrade() -> None:
    op.drop_table("client_admins")
