"""Chuyen ORM -> schema dung chung giua nhieu router (tranh lap lai va lech du lieu)."""
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app import schemas
from app.db import models


def face_status_of(student: models.Student) -> str:
    statuses = {e.status for e in student.embeddings}
    for status in ("approved", "pending", "rejected"):
        if status in statuses:
            return status
    return "none"


def student_out(s: models.Student, out_cls=schemas.StudentOut, **extra):
    return out_cls(
        id=s.id, student_code=s.student_code, full_name=s.user.full_name,
        major=s.major, cohort=s.cohort,
        face_enrolled=any(e.status == "approved" for e in s.embeddings),
        face_status=face_status_of(s),
        consent_given=s.consent_given, consent_version=s.consent_version,
        consent_method=s.consent_method, consent_recorded_by=s.consent_recorded_by,
        faculty_id=s.faculty_id, faculty_name=s.faculty.name if s.faculty else None,
        email=s.user.email,
        **extra,
    )


def lecturer_out(l: models.Lecturer) -> schemas.LecturerOut:
    return schemas.LecturerOut(
        id=l.id, lecturer_code=l.lecturer_code, full_name=l.user.full_name,
        department=l.department, email=l.user.email,
        faculty_id=l.faculty_id, faculty_name=l.faculty.name if l.faculty else None,
    )


def class_out(c: models.Class, student_count: int | None = None) -> schemas.ClassOut:
    return schemas.ClassOut(
        id=c.id, class_code=c.class_code, subject_name=c.subject_name,
        lecturer_id=c.lecturer_id, semester=c.semester, faculty_id=c.faculty_id,
        lecturer_name=c.lecturer.user.full_name if c.lecturer else None,
        faculty_name=c.faculty.name if c.faculty else None,
        student_count=student_count,
    )


def staff_out(st: models.Staff) -> schemas.StaffOut:
    return schemas.StaffOut(
        id=st.id, user_id=st.user_id, email=st.user.email, full_name=st.user.full_name,
        role=st.user.role, unit_id=st.unit_id, unit_code=st.unit.code,
        unit_name=st.unit.name, unit_type=st.unit.type, position=st.position,
    )


def ensure_email_available(db: Session, email: str) -> None:
    if db.query(models.User).filter(models.User.email == email).first():
        raise HTTPException(400, "Email da ton tai")


def delete_user_auth_rows(db: Session, user_id: int) -> None:
    """Xoa du lieu xac thuc phu thuoc user (OTP, refresh token) truoc khi xoa user."""
    db.query(models.PasswordReset).filter_by(user_id=user_id).delete()
    db.query(models.RefreshToken).filter_by(user_id=user_id).delete()


def ensure_no_audit_history(db: Session, user_id: int) -> None:
    if db.query(models.AttendanceAudit).filter_by(changed_by=user_id).first():
        raise HTTPException(
            409, "Tai khoan da co lich su sua diem danh, khong the xoa (giu lai de doi chieu)")


def room_label(schedule: models.Schedule) -> str:
    """Ten phong de hien thi: uu tien danh muc phong, con lai lay o chu cu cua lich."""
    return schedule.classroom.name if schedule.classroom is not None else schedule.room


def schedule_out(s: models.Schedule) -> schemas.ScheduleOut:
    return schemas.ScheduleOut(
        id=s.id, class_id=s.class_id, weekday=s.weekday,
        start_time=s.start_time, end_time=s.end_time,
        room=s.room, room_id=s.room_id,
        room_name=s.classroom.name if s.classroom else None,
        location_id=s.location_id,
    )
