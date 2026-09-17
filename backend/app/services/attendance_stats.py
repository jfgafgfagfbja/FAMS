"""Thong ke chuyen can dung chung cho bao cao, dong phien va thong ke tong hop."""
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import models

STATUSES = ("present", "late", "absent", "excused", "manual")


def compute_class_attendance_stats(db: Session, class_id: int) -> list[dict]:
    """Thong ke chuyen can tung SV trong lop: so buoi present/late/absent/excused/manual,
    ti le vang (khong tinh excused) va co vuot ABSENCE_WARN_RATIO hay khong.

    Chi tinh phien DA DONG - ca tu so (so buoi) lan mau so (tong buoi), tranh ti le lech
    khi dang co phien mo (record co mat da ghi nhung phien chua duoc tinh vao tong).
    """
    total_sessions = (
        db.query(func.count(models.AttendanceSession.id))
        .join(models.Schedule)
        .filter(models.Schedule.class_id == class_id,
                models.AttendanceSession.status == "closed")
        .scalar()
    ) or 0

    rows = (
        db.query(models.AttendanceRecord.student_id,
                 models.AttendanceRecord.status,
                 func.count().label("cnt"))
        .join(models.AttendanceSession)
        .join(models.Schedule)
        .filter(models.Schedule.class_id == class_id,
                models.AttendanceSession.status == "closed")
        .group_by(models.AttendanceRecord.student_id,
                  models.AttendanceRecord.status)
        .all()
    )

    stats: dict[int, dict] = {}
    for student_id, status, cnt in rows:
        stats.setdefault(student_id, {s: 0 for s in STATUSES})
        stats[student_id][status] = cnt

    result = []
    for student_id, s in stats.items():
        student = db.get(models.Student, student_id)
        # excused khong tinh la vang khi xet canh bao chuyen can
        absent_ratio = s["absent"] / total_sessions if total_sessions else 0
        result.append({
            "student_id": student_id,
            "student_code": student.student_code,
            "full_name": student.user.full_name,
            **s,
            "total_sessions": total_sessions,
            "absent_ratio": round(absent_ratio, 4),
            "warning": absent_ratio >= settings.ABSENCE_WARN_RATIO,
        })
    result.sort(key=lambda r: r["student_code"])
    return result
