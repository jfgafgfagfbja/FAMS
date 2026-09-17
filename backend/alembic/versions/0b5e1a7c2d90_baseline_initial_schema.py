"""baseline: bang goc truoc khi dung Alembic

Truoc day schema ban dau duoc tao bang Base.metadata.create_all() (khong co migration),
migration dau tien 150e85d92f65 chi THEM cot vao bang co san -> `alembic upgrade head`
tren database trong (volume Docker moi, CI) loi "relation students does not exist".

Migration nay tao lai dung schema ban dau (commit 13f0543, bo cac cot/bang do migration
sau them vao). DB cu da co bang (tao bang create_all) se bo qua - idempotent.

Revision ID: 0b5e1a7c2d90
Revises:
Create Date: 2026-07-14 08:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import pgvector.sqlalchemy
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0b5e1a7c2d90'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    if sa.inspect(bind).has_table("users"):
        return  # DB tao tu truoc bang create_all

    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
    )
    op.create_table(
        'students',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('student_code', sa.String(length=20), nullable=False),
        sa.Column('major', sa.String(length=100), nullable=False),
        sa.Column('cohort', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('student_code'),
    )
    op.create_table(
        'lecturers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('lecturer_code', sa.String(length=20), nullable=False),
        sa.Column('department', sa.String(length=100), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('lecturer_code'),
    )
    op.create_table(
        'classes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('class_code', sa.String(length=30), nullable=False),
        sa.Column('subject_name', sa.String(length=255), nullable=False),
        sa.Column('lecturer_id', sa.Integer(), nullable=False),
        sa.Column('semester', sa.String(length=20), nullable=False),
        sa.ForeignKeyConstraint(['lecturer_id'], ['lecturers.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('class_code'),
    )
    op.create_table(
        'enrollments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('class_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['class_id'], ['classes.id']),
        sa.ForeignKeyConstraint(['student_id'], ['students.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('student_id', 'class_id'),
    )
    op.create_table(
        'schedules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('class_id', sa.Integer(), nullable=False),
        sa.Column('weekday', sa.Integer(), nullable=False),
        sa.Column('start_time', sa.Time(), nullable=False),
        sa.Column('end_time', sa.Time(), nullable=False),
        sa.Column('room', sa.String(length=50), nullable=False),
        sa.ForeignKeyConstraint(['class_id'], ['classes.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'attendance_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('schedule_id', sa.Integer(), nullable=False),
        sa.Column('session_date', sa.Date(), nullable=False),
        sa.Column('opened_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('closed_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(length=10), nullable=False),
        sa.ForeignKeyConstraint(['schedule_id'], ['schedules.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'attendance_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('checked_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('status', sa.String(length=10), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('evidence_image', sa.String(length=500), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['attendance_sessions.id']),
        sa.ForeignKeyConstraint(['student_id'], ['students.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_id', 'student_id'),
    )
    op.create_table(
        'face_embeddings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('embedding', pgvector.sqlalchemy.Vector(dim=512), nullable=False),
        sa.Column('source_image', sa.String(length=500), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['student_id'], ['students.id']),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    for table in ('face_embeddings', 'attendance_records', 'attendance_sessions', 'schedules',
                  'enrollments', 'classes', 'lecturers', 'students', 'users'):
        op.drop_table(table)
