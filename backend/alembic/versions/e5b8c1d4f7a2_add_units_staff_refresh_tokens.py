"""add units (khoa/phong/ban), staff, refresh_tokens, users.token_version, faculty_id links

Don vi moi (units) dung cho phan quyen Phong Dao tao, Phong Cong tac SV, Khoa, Ban nganh.
faculty_id tren students/lecturers/classes de nullable: du lieu cu chua gan Khoa (admin gan
sau qua giao dien) - can bo Khoa chi thay SV/GV/lop da duoc gan dung Khoa cua minh.

Revision ID: e5b8c1d4f7a2
Revises: a18f6c2b9e40
Create Date: 2026-09-17 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5b8c1d4f7a2'
down_revision: Union[str, Sequence[str], None] = 'a18f6c2b9e40'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

FACULTY_LINK_TABLES = ("students", "lecturers", "classes")


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'units',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=30), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('type', sa.String(length=20), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code'),
    )
    op.create_table(
        'staff',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('unit_id', sa.Integer(), nullable=False),
        sa.Column('position', sa.String(length=100), nullable=False, server_default=''),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['unit_id'], ['units.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id'),
    )
    op.create_table(
        'refresh_tokens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('revoked_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token_hash'),
    )
    op.add_column('users', sa.Column('token_version', sa.Integer(), nullable=False,
                                     server_default='0'))
    for table in FACULTY_LINK_TABLES:
        op.add_column(table, sa.Column('faculty_id', sa.Integer(), nullable=True))
        op.create_foreign_key(f'fk_{table}_faculty_id_units', table, 'units',
                              ['faculty_id'], ['id'])


def downgrade() -> None:
    """Downgrade schema."""
    for table in FACULTY_LINK_TABLES:
        op.drop_constraint(f'fk_{table}_faculty_id_units', table, type_='foreignkey')
        op.drop_column(table, 'faculty_id')
    op.drop_column('users', 'token_version')
    op.drop_table('refresh_tokens')
    op.drop_table('staff')
    op.drop_table('units')
