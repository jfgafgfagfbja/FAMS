import io

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.authz import ensure_class_access
from app.core.config import settings
from app.core.security import get_current_user
from app.db import models
from app.db.database import get_db

router = APIRouter(prefix="/reports", tags=["reports"])

STATUS_LETTER = {"present": "P", "late": "L", "absent": "A", "excused": "E", "manual": "M"}
RED_FILL = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")


def compute_class_attendance_stats(db: Session, class_id: int) -> list[dict]:
    """Thong ke chuyen can tung SV trong lop: so buoi present/late/absent/excused/manual,
    ti le vang (khong tinh excused) va co vuot ABSENCE_WARN_RATIO hay khong.

    Dung chung cho GET /attendance/{class_id}, /attendance/warnings va export Excel.
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
        .filter(models.Schedule.class_id == class_id)
        .group_by(models.AttendanceRecord.student_id,
                  models.AttendanceRecord.status)
        .all()
    )

    stats: dict[int, dict] = {}
    for student_id, status, cnt in rows:
        stats.setdefault(student_id, {"present": 0, "late": 0,
                                      "absent": 0, "excused": 0, "manual": 0})
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
            "warning": absent_ratio >= settings.ABSENCE_WARN_RATIO,
        })
    return result


@router.get("/attendance/warnings")
def attendance_warnings(
    class_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """Danh sach SV vuot nguong vang (absent / tong buoi da hoc >= ABSENCE_WARN_RATIO).
    excused khong tinh la vang."""
    ensure_class_access(user, class_id, db)
    return [r for r in compute_class_attendance_stats(db, class_id) if r["warning"]]


@router.get("/attendance/export")
def export_attendance(
    class_id: int,
    semester: str,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """Xuat file Excel diem danh: sheet 1 la ma tran SV x buoi hoc, sheet 2 la
    thong ke tong hop lop. Chi lecturer cua lop hoac admin."""
    ensure_class_access(user, class_id, db)

    clazz = db.get(models.Class, class_id)
    if not clazz:
        raise HTTPException(404, "Lop hoc phan khong ton tai")
    if clazz.semester != semester:
        raise HTTPException(
            400, f"Lop {clazz.class_code} thuoc hoc ky {clazz.semester}, khong phai {semester}")

    sessions = (
        db.query(models.AttendanceSession)
        .join(models.Schedule)
        .filter(models.Schedule.class_id == class_id,
                models.AttendanceSession.status == "closed")
        .order_by(models.AttendanceSession.session_date)
        .all()
    )
    students = (
        db.query(models.Student)
        .join(models.Enrollment, models.Enrollment.student_id == models.Student.id)
        .filter(models.Enrollment.class_id == class_id)
        .order_by(models.Student.student_code)
        .all()
    )
    records = (
        db.query(models.AttendanceRecord)
        .join(models.AttendanceSession)
        .join(models.Schedule)
        .filter(models.Schedule.class_id == class_id,
                models.AttendanceSession.status == "closed")
        .all()
    )
    record_by_session_student = {(r.session_id, r.student_id): r.status for r in records}

    total_sessions = len(sessions)

    wb = Workbook()
    ws1 = wb.active
    ws1.title = "Diem danh"

    header = (["MSSV", "Ho ten"]
              + [s.session_date.strftime("%d/%m/%Y") for s in sessions]
              + ["Tong vang", "% vang"])
    ws1.append(header)
    for cell in ws1[1]:
        cell.font = Font(bold=True)

    warning_count = 0
    for student in students:
        row = [student.student_code, student.user.full_name]
        absent_count = 0
        for session in sessions:
            status = record_by_session_student.get((session.id, student.id))
            row.append(STATUS_LETTER.get(status, ""))
            if status == "absent":
                absent_count += 1
        ratio = absent_count / total_sessions if total_sessions else 0
        row.append(absent_count)
        row.append(f"{ratio * 100:.1f}%")
        ws1.append(row)

        if ratio >= settings.ABSENCE_WARN_RATIO:
            warning_count += 1
            for cell in ws1[ws1.max_row]:
                cell.fill = RED_FILL

    for col in ws1.columns:
        values = [str(c.value) for c in col if c.value is not None]
        width = max((len(v) for v in values), default=10)
        ws1.column_dimensions[col[0].column_letter].width = width + 2

    ws2 = wb.create_sheet("Thong ke lop")
    summary_rows = [
        ("Ma lop", clazz.class_code),
        ("Mon hoc", clazz.subject_name),
        ("Hoc ky", clazz.semester),
        ("Tong so sinh vien", len(students)),
        ("Tong so buoi da diem danh", total_sessions),
        ("So SV vuot nguong canh bao vang", warning_count),
        ("Nguong canh bao (%)", f"{settings.ABSENCE_WARN_RATIO * 100:.0f}%"),
    ]
    for label, value in summary_rows:
        ws2.append([label, value])
    for row in ws2.iter_rows(min_row=1, max_row=len(summary_rows), min_col=1, max_col=1):
        for cell in row:
            cell.font = Font(bold=True)
    ws2.column_dimensions["A"].width = 30
    ws2.column_dimensions["B"].width = 20

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    filename = f"diemdanh_{clazz.class_code}_{semester}.xlsx"
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/attendance/{class_id}")
def class_attendance(
    class_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """Thong ke chuyen can theo lop: ti le vang tung SV + canh bao."""
    ensure_class_access(user, class_id, db)
    return compute_class_attendance_stats(db, class_id)


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

        counts = {"present": 0, "late": 0, "absent": 0, "excused": 0, "manual": 0}
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

        # excused khong tinh la vang khi xet canh bao chuyen can
        absent_ratio = counts["absent"] / total_sessions if total_sessions else 0
        result.append({
            "class_code": clazz.class_code,
            "subject_name": clazz.subject_name,
            **counts,
            "total_sessions": total_sessions,
            "warning": absent_ratio >= settings.ABSENCE_WARN_RATIO,
        })
    return result
