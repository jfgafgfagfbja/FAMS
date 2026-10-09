"""them danh muc phong hoc va gan lich hoc vao phong

Revision ID: c3d9f61a84b7
Revises: f7c2a9d1e3b4
Create Date: 2026-10-09

Truoc day phong hoc chi la mot o chu tu do tren lich (schedules.room), nen cung mot
phong bi go nhieu kieu khac nhau va khong gan duoc toa do. Ban nay tao bang rooms,
sinh san phong tu cac gia tri dang co roi tro lich hoc vao day.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'c3d9f61a84b7'
down_revision: Union[str, Sequence[str], None] = 'f7c2a9d1e3b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'rooms',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=30), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('building', sa.String(length=100), nullable=True),
        sa.Column('floor', sa.Integer(), nullable=True),
        sa.Column('capacity', sa.Integer(), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('radius_m', sa.Float(), nullable=True),
        sa.Column('location_id', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(['location_id'], ['locations.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code'),
    )
    op.create_index('ix_rooms_location_id', 'rooms', ['location_id'])

    op.add_column('schedules', sa.Column('room_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_schedules_room_id', 'schedules', 'rooms', ['room_id'], ['id'])
    op.create_index('ix_schedules_room_id', 'schedules', ['room_id'])

    _seed_rooms_from_schedules()


def _seed_rooms_from_schedules() -> None:
    """Sinh phong tu cac chuoi dang co trong schedules.room va tro lich vao phong do.

    Chi chay khi da co mot dia diem de gan phong vao (uu tien dia diem mac dinh).
    Chua co dia diem nao thi bo qua - quan tri se tu tao phong sau, lich cu van chay
    binh thuong vi cot `room` dang chu duoc giu nguyen.
    """
    bind = op.get_bind()
    location_id = bind.execute(sa.text(
        "SELECT id FROM locations ORDER BY is_default DESC, id LIMIT 1")).scalar()
    if location_id is None:
        return

    rows = bind.execute(sa.text(
        "SELECT DISTINCT room FROM schedules WHERE room IS NOT NULL AND btrim(room) <> ''")).all()
    for (raw,) in rows:
        code = raw.strip().upper()
        if not code:
            continue
        existing = bind.execute(sa.text("SELECT id FROM rooms WHERE code = :code"),
                                {"code": code}).scalar()
        if existing is None:
            existing = bind.execute(
                sa.text("INSERT INTO rooms (code, name, location_id, is_active) "
                        "VALUES (:code, :name, :loc, true) RETURNING id"),
                {"code": code[:30], "name": f"Phong {raw.strip()}"[:255], "loc": location_id},
            ).scalar()
        bind.execute(sa.text("UPDATE schedules SET room_id = :rid WHERE btrim(room) = :raw"),
                     {"rid": existing, "raw": raw.strip()})


def downgrade() -> None:
    op.drop_index('ix_schedules_room_id', table_name='schedules')
    op.drop_constraint('fk_schedules_room_id', 'schedules', type_='foreignkey')
    op.drop_column('schedules', 'room_id')
    op.drop_index('ix_rooms_location_id', table_name='rooms')
    op.drop_table('rooms')
