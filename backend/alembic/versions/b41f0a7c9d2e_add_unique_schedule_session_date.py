"""add unique constraint (schedule_id, session_date) on attendance_sessions

Truoc khi tao rang buoc: don du lieu trung san co - moi nhom (schedule_id,
session_date) chi giu lai phien MOI NHAT (opened_at lon nhat, tie-break theo id),
cac phien cu hon bi xoa kem record/audit cua chung va duoc log ra console.

Revision ID: b41f0a7c9d2e
Revises: 3243764e3dbd
Create Date: 2026-07-16 09:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b41f0a7c9d2e'
down_revision: Union[str, Sequence[str], None] = '3243764e3dbd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

UQ_NAME = "uq_attendance_sessions_schedule_id_session_date"


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()

    dup_groups = bind.execute(sa.text(
        """
        SELECT schedule_id, session_date,
               array_agg(id ORDER BY opened_at DESC NULLS LAST, id DESC) AS ids
        FROM attendance_sessions
        GROUP BY schedule_id, session_date
        HAVING count(*) > 1
        """
    )).fetchall()

    for row in dup_groups:
        keep_id, *drop_ids = row.ids
        n_records = bind.execute(sa.text(
            "SELECT count(*) FROM attendance_records WHERE session_id = ANY(:ids)"
        ), {"ids": drop_ids}).scalar()
        print(
            f"[b41f0a7c9d2e] schedule_id={row.schedule_id} session_date={row.session_date}: "
            f"giu phien id={keep_id}, xoa {len(drop_ids)} phien trung {drop_ids} "
            f"(kem {n_records} attendance_records)"
        )
        bind.execute(sa.text(
            """
            DELETE FROM attendance_audits
            WHERE record_id IN (SELECT id FROM attendance_records WHERE session_id = ANY(:ids))
            """
        ), {"ids": drop_ids})
        bind.execute(sa.text(
            "DELETE FROM attendance_records WHERE session_id = ANY(:ids)"
        ), {"ids": drop_ids})
        bind.execute(sa.text(
            "DELETE FROM attendance_sessions WHERE id = ANY(:ids)"
        ), {"ids": drop_ids})

    op.create_unique_constraint(
        UQ_NAME, "attendance_sessions", ["schedule_id", "session_date"])


def downgrade() -> None:
    """Downgrade schema. (Du lieu da xoa khi upgrade khong khoi phuc duoc.)"""
    op.drop_constraint(UQ_NAME, "attendance_sessions", type_="unique")
