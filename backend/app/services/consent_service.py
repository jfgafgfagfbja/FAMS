"""Ghi nhan va rut dong y su dung du lieu khuon mat (xem core/consent.py)."""
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.consent import CONSENT_VERSION
from app.core.media import delete_media
from app.db import models


def record_consent(student: models.Student, method: str, recorded_by: str) -> None:
    student.consent_given = True
    student.consent_given_at = datetime.now()
    student.consent_version = CONSENT_VERSION
    student.consent_method = method
    student.consent_recorded_by = recorded_by


def withdraw_consent(db: Session, student: models.Student) -> int:
    """Rut dong y: xoa NGAY toan bo anh va vector khuon mat cua SV, xoa dau dong y. Tra ve
    so mau khuon mat da xoa. Nguoi goi tu commit."""
    embeddings = db.query(models.FaceEmbedding).filter_by(student_id=student.id).all()
    for emb in embeddings:
        delete_media(emb.source_image)
        db.delete(emb)
    student.consent_given = False
    student.consent_given_at = None
    student.consent_version = None
    student.consent_method = None
    student.consent_recorded_by = None
    return len(embeddings)
