"""set database default timezone to Asia/Ho_Chi_Minh

Bug: attendance_records.checked_at dung server_default=func.now() - PostgreSQL
tinh gio nay theo TimeZone cua SESSION/DATABASE, KHONG lien quan gi den bien
moi truong TZ cua container backend (chi anh huong datetime.now() phia Python).
Container db trong docker-compose.yml truoc gio chua khai bao TZ nen mac dinh
tinh theo UTC, lech 7 tieng so voi gio Viet Nam ma toan bo logic con lai cua he
thong (mo/dong phien, tre/dung gio...) dang dung. Set o cap DATABASE de co hieu
luc ngay ca voi volume du lieu da khoi tao tu truoc (khong can wipe volume).

Revision ID: a18f6c2b9e40
Revises: d7c9a3f21b4e
Create Date: 2026-09-06 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'a18f6c2b9e40'
down_revision: Union[str, Sequence[str], None] = 'd7c9a3f21b4e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    dbname = bind.engine.url.database
    op.execute(f'ALTER DATABASE "{dbname}" SET timezone TO \'Asia/Ho_Chi_Minh\'')


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    dbname = bind.engine.url.database
    op.execute(f'ALTER DATABASE "{dbname}" SET timezone TO DEFAULT')
