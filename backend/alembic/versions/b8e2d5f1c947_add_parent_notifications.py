"""thong bao diem danh cho phu huynh: hop thu + hang doi email, tuy chon nhan tin

Revision ID: b8e2d5f1c947
Revises: a71c4e9d3b82
Create Date: 2026-10-09
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'b8e2d5f1c947'
down_revision: Union[str, Sequence[str], None] = 'a71c4e9d3b82'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'notifications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('kind', sa.String(length=30), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('link', sa.String(length=255), nullable=True),
        sa.Column('record_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('read_at', sa.DateTime(), nullable=True),
        sa.Column('email_status', sa.String(length=10), nullable=False, server_default='skipped'),
        sa.Column('email_attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('email_error', sa.String(length=255), nullable=True),
        sa.Column('emailed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['record_id'], ['attendance_records.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'record_id', 'kind'),
    )
    op.create_index('ix_notifications_user_id', 'notifications', ['user_id'])
    # Tac vu gui email chi quet cac dong dang cho - chi muc mot phan cho nhanh.
    op.create_index('ix_notifications_email_pending', 'notifications', ['id'],
                    postgresql_where=sa.text("email_status = 'pending'"))

    op.add_column('parents', sa.Column('notify_email', sa.Boolean(), nullable=False,
                                       server_default=sa.true()))
    op.add_column('parents', sa.Column('notify_present', sa.Boolean(), nullable=False,
                                       server_default=sa.true()))


def downgrade() -> None:
    op.drop_column('parents', 'notify_present')
    op.drop_column('parents', 'notify_email')
    op.drop_index('ix_notifications_email_pending', table_name='notifications')
    op.drop_index('ix_notifications_user_id', table_name='notifications')
    op.drop_table('notifications')
