"""them co yeu cau quet ma QR cho phien diem danh

Revision ID: a71c4e9d3b82
Revises: c3d9f61a84b7
Create Date: 2026-10-09

GPS chi xac nhan duoc sinh vien o trong khu vuc, khong biet dung phong hay khong.
Bat co nay thi SV phai quet ma QR dang chieu trong phong moi tu diem danh duoc.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'a71c4e9d3b82'
down_revision: Union[str, Sequence[str], None] = 'c3d9f61a84b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('attendance_sessions',
                  sa.Column('require_qr', sa.Boolean(), nullable=False,
                            server_default=sa.false()))


def downgrade() -> None:
    op.drop_column('attendance_sessions', 'require_qr')
