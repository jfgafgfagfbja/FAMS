"""add locations (dia diem diem danh), schedules.location_id, attendance_records.distance_m

Revision ID: f7c2a9d1e3b4
Revises: e5b8c1d4f7a2
Create Date: 2026-09-18 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f7c2a9d1e3b4'
down_revision: Union[str, Sequence[str], None] = 'e5b8c1d4f7a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'locations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=30), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('radius_m', sa.Float(), nullable=False, server_default='150'),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code'),
    )
    op.add_column('schedules', sa.Column('location_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_schedules_location_id_locations', 'schedules', 'locations',
                          ['location_id'], ['id'])
    op.add_column('attendance_records', sa.Column('distance_m', sa.Float(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('attendance_records', 'distance_m')
    op.drop_constraint('fk_schedules_location_id_locations', 'schedules', type_='foreignkey')
    op.drop_column('schedules', 'location_id')
    op.drop_table('locations')
