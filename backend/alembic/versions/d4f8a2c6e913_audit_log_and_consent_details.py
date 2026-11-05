"""nhat ky he thong; chi tiet dong y sinh trac hoc (phien ban, cach dong y, nguoi ghi nhan)

Revision ID: d4f8a2c6e913
Revises: b8e2d5f1c947
Create Date: 2026-10-16

Vai tro Lanh dao Khoa (faculty_leader) chi la mot gia tri moi cua cot users.role (chuoi),
khong can doi cau truc.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'd4f8a2c6e913'
down_revision: Union[str, Sequence[str], None] = 'b8e2d5f1c947'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('actor_id', sa.Integer(), nullable=True),
        sa.Column('actor_email', sa.String(length=255), nullable=True),
        sa.Column('actor_role', sa.String(length=30), nullable=True),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('target_type', sa.String(length=30), nullable=True),
        sa.Column('target_id', sa.Integer(), nullable=True),
        sa.Column('target_label', sa.String(length=255), nullable=True),
        sa.Column('faculty_id', sa.Integer(), nullable=True),
        sa.Column('ip', sa.String(length=64), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('detail', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['actor_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['faculty_id'], ['units.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_audit_logs_created_at', 'audit_logs', ['created_at'])
    op.create_index('ix_audit_logs_actor_id', 'audit_logs', ['actor_id'])
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'])
    op.create_index('ix_audit_logs_faculty_id', 'audit_logs', ['faculty_id'])

    op.add_column('students', sa.Column('consent_version', sa.String(length=20), nullable=True))
    op.add_column('students', sa.Column('consent_method', sa.String(length=10), nullable=True))
    op.add_column('students', sa.Column('consent_recorded_by', sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column('students', 'consent_recorded_by')
    op.drop_column('students', 'consent_method')
    op.drop_column('students', 'consent_version')
    op.drop_index('ix_audit_logs_faculty_id', table_name='audit_logs')
    op.drop_index('ix_audit_logs_action', table_name='audit_logs')
    op.drop_index('ix_audit_logs_actor_id', table_name='audit_logs')
    op.drop_index('ix_audit_logs_created_at', table_name='audit_logs')
    op.drop_table('audit_logs')
