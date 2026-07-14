"""add hnsw index on face_embeddings

Revision ID: 3425299cc20d
Revises: 619a843979a7
Create Date: 2026-07-14 15:58:16.043254

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3425299cc20d'
down_revision: Union[str, Sequence[str], None] = '619a843979a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # HNSW cho cosine distance (<=>) - dung cho recognize_frame/enroll_face trong
    # face_service.py. op.create_index khong ho tro truc tiep access method +
    # operator class kieu nay nen dung raw SQL.
    op.execute(
        "CREATE INDEX ix_face_embeddings_embedding_hnsw ON face_embeddings "
        "USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP INDEX IF EXISTS ix_face_embeddings_embedding_hnsw")
