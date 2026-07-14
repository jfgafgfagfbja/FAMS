from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.authz import ensure_class_access
from app.core.security import get_current_user
from app.db import models
from app.db.database import get_db

router = APIRouter(prefix="/reports", tags=["reports"])

ABSENT_WARNING_RATIO = 0.2  # vang > 20% so buoi -> canh bao cam thi


@router.get("/attendance/{class_id}")
def class_attendance(
    class_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """Thong ke chuyen can theo lop: ti le vang tung SV + canh bao."""
    ensure_class_access(user, class_id, db)

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
        .filter(models.Schedule.class_id == class_id)
        .group_by(models.AttendanceRecord.student_id,
                  models.AttendanceRecord.status)
        .all()
    )

    stats: dict[int, dict] = {}
    for student_id, status, cnt in rows:
        stats.setdefault(student_id, {"present": 0, "late": 0,
                                      "absent": 0, "manual": 0})
        stats[student_id][status] = cnt

    result = []
    for student_id, s in stats.items():
        student = db.get(models.Student, student_id)
        absent_ratio = s["absent"] / total_sessions if total_sessions else 0
        result.append({
            "student_code": student.student_code,
            "full_name": student.user.full_name,
            **s,
            "total_sessions": total_sessions,
            "warning": absent_ratio > ABSENT_WARNING_RATIO,
        })
    return result


@router.get("/my-attendance")
def my_attendance(
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """Sinh vien tu xem lich su diem danh cua chinh minh, theo tung lop da dang ky."""
    if user.role != "student":
        raise HTTPException(403, "Chi sinh vien moi xem duoc muc nay")
    student = db.query(models.Student).filter_by(user_id=user.id).first()
    if not student:
        raise HTTPException(404, "Khong tim thay ho so sinh vien")

    result = []
    for enrollment in student.enrollments:
        clazz = enrollment.clazz
        total_sessions = (
            db.query(func.count(models.AttendanceSession.id))
            .join(models.Schedule)
            .filter(models.Schedule.class_id == clazz.id,
                    models.AttendanceSession.status == "closed")
            .scalar()
        ) or 0

        counts = {"present": 0, "late": 0, "absent": 0, "manual": 0}
        rows = (
            db.query(models.AttendanceRecord.status, func.count().label("cnt"))
            .join(models.AttendanceSession)
            .join(models.Schedule)
            .filter(models.Schedule.class_id == clazz.id,
                    models.AttendanceRecord.student_id == student.id)
            .group_by(models.AttendanceRecord.status)
            .all()
        )
        for status, cnt in rows:
            counts[status] = cnt

        absent_ratio = counts["absent"] / total_sessions if total_sessions else 0
        result.append({
            "class_code": clazz.class_code,
            "subject_name": clazz.subject_name,
            **counts,
            "total_sessions": total_sessions,
            "warning": absent_ratio > ABSENT_WARNING_RATIO,
        })
    return result
