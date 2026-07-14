"""add status and reject reason to face embeddings

Revision ID: 1d8874f7a39c
Revises: 3425299cc20d
Create Date: 2026-07-14 23:25:58.164449

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1d8874f7a39c'
down_revision: Union[str, Sequence[str], None] = '3425299cc20d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # server_default="approved" khi them cot: cac embedding da co tu truoc (dang
    # duoc dung song cho nhan dien) duoc giu nguyen hieu luc thay vi bi khoa lai
    # thanh cho duyet. Insert moi ve sau se tu chi dinh status="pending" o tang
    # ung dung (xem face_service.enroll_face), nen doi lai server_default thanh
    # "pending" ngay sau do de khop dung mac dinh mong muon cho hang moi.
    op.add_column(
        "face_embeddings",
        sa.Column("status", sa.String(length=10), nullable=False, server_default="approved"),
    )
    op.alter_column("face_embeddings", "status", server_default="pending")
    op.add_column(
        "face_embeddings",
        sa.Column("reject_reason", sa.String(length=500), nullable=False, server_default=""),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("face_embeddings", "reject_reason")
    op.drop_column("face_embeddings", "status")
