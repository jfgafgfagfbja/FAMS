"""add password reset otp table and credentials changed at

Revision ID: 3243764e3dbd
Revises: 1d8874f7a39c
Create Date: 2026-07-15 01:59:01.934825

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3243764e3dbd'
down_revision: Union[str, Sequence[str], None] = '1d8874f7a39c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "users",
        sa.Column("credentials_changed_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "password_resets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("otp_hash", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("used", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("password_resets")
    op.drop_column("users", "credentials_changed_at")
