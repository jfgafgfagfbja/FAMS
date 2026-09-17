"""add parents/parent_students tables and location+source fields on attendance_records

Revision ID: d7c9a3f21b4e
Revises: b41f0a7c9d2e
Create Date: 2026-09-05 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd7c9a3f21b4e'
down_revision: Union[str, Sequence[str], None] = 'b41f0a7c9d2e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'parents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('phone', sa.String(length=20), nullable=False, server_default=''),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'parent_students',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('parent_id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['parent_id'], ['parents.id']),
        sa.ForeignKeyConstraint(['student_id'], ['students.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('parent_id', 'student_id'),
    )

    op.add_column(
        'attendance_records',
        sa.Column('source', sa.String(length=10), nullable=False, server_default='camera'))
    op.add_column('attendance_records', sa.Column('latitude', sa.Float(), nullable=True))
    op.add_column('attendance_records', sa.Column('longitude', sa.Float(), nullable=True))
    op.add_column('attendance_records', sa.Column('location_accuracy', sa.Float(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('attendance_records', 'location_accuracy')
    op.drop_column('attendance_records', 'longitude')
    op.drop_column('attendance_records', 'latitude')
    op.drop_column('attendance_records', 'source')
    op.drop_table('parent_students')
    op.drop_table('parents')
