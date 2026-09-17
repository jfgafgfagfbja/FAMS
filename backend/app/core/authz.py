"""Phan quyen theo vai tro va pham vi du lieu.

Ma tran quyen (Sua = tao/sua/xoa, Xem = chi doc, * = chi trong Khoa cua minh):

  Chuc nang                  Admin  P.DaoTao  P.CTSV  Khoa   Ban nganh
  Tai khoan can bo, don vi   Sua    -         -       -      -
  Lop HP, lich, ghi danh     Sua    Sua       Xem     Xem*   -
  Ho so GV, phan cong GV     Sua    Sua       -       Xem*   -
  Ho so SV, phu huynh        Sua    Xem       Sua     Xem*   -
  Duyet khuon mat            Sua    -         Sua     -      -
  Diem danh chi tiet + anh   Sua    Xem       Xem     Xem*   -
  Duyet "Co phep"            Sua    -         Sua     Sua*   -
  Canh bao vang, xuat Excel  Xem    Xem       Xem     Xem*   -
  Thong ke tong hop          Xem    Xem       Xem     Xem*   Xem

Giang vien: mo phien/quet camera/sua diem danh lop minh day. SV/phu huynh: du lieu cua minh/con.
"""
from fastapi import HTTPException, status
from sqlalchemy import false
from sqlalchemy.orm import Query, Session

from app.db import models
from app.db.models import (ROLE_ADMIN, ROLE_AFFAIRS, ROLE_BOARD, ROLE_FACULTY, ROLE_LECTURER,
                           ROLE_PARENT, ROLE_STUDENT, ROLE_TRAINING)

# Xem chi tiet (ten, anh bang chung...) toan truong.
SCHOOL_WIDE_VIEWERS = (ROLE_ADMIN, ROLE_TRAINING, ROLE_AFFAIRS)
# Nhom duoc xem chi tiet lop/phien/bao cao (co gioi han pham vi voi Khoa, GV).
CLASS_VIEWERS = (ROLE_ADMIN, ROLE_TRAINING, ROLE_AFFAIRS, ROLE_FACULTY, ROLE_LECTURER)
# Quan ly hoc vu: lop hoc phan, lich hoc, ghi danh, ho so giang vien.
ACADEMIC_MANAGERS = (ROLE_ADMIN, ROLE_TRAINING)
# Quan ly ho so SV, phu huynh, duyet khuon mat.
STUDENT_MANAGERS = (ROLE_ADMIN, ROLE_AFFAIRS)
# Duoc xem thong ke tong hop (khong co ten/anh).
OVERVIEW_VIEWERS = (ROLE_ADMIN, ROLE_TRAINING, ROLE_AFFAIRS, ROLE_FACULTY, ROLE_BOARD)

_FORBIDDEN = "Khong co quyen voi du lieu nay"


def _forbid(detail: str = _FORBIDDEN) -> HTTPException:
    return HTTPException(status.HTTP_403_FORBIDDEN, detail)


def staff_profile(user: models.User, db: Session) -> models.Staff | None:
    return db.query(models.Staff).filter_by(user_id=user.id).first()


def staff_unit_id(user: models.User, db: Session) -> int | None:
    staff = staff_profile(user, db)
    return staff.unit_id if staff else None


def lecturer_profile(user: models.User, db: Session) -> models.Lecturer | None:
    return db.query(models.Lecturer).filter_by(user_id=user.id).first()


# ---------------- Lop hoc phan ----------------

def ensure_class_access(user: models.User, class_id: int, db: Session) -> None:
    """Quyen THAO TAC diem danh cua lop: admin moi lop, giang vien chi lop minh day."""
    if user.role == ROLE_ADMIN:
        return
    if user.role == ROLE_LECTURER:
        lecturer = lecturer_profile(user, db)
        clazz = db.get(models.Class, class_id)
        if lecturer and clazz and clazz.lecturer_id == lecturer.id:
            return
    raise _forbid("Khong co quyen voi lop hoc phan nay")


def can_view_class(user: models.User, clazz: models.Class, db: Session) -> bool:
    if user.role in SCHOOL_WIDE_VIEWERS:
        return True
    if user.role == ROLE_FACULTY:
        unit_id = staff_unit_id(user, db)
        return unit_id is not None and clazz.faculty_id == unit_id
    if user.role == ROLE_LECTURER:
        lecturer = lecturer_profile(user, db)
        return lecturer is not None and clazz.lecturer_id == lecturer.id
    return False


def ensure_class_view(user: models.User, class_id: int, db: Session) -> models.Class:
    """Quyen XEM chi tiet lop (DS SV, phien, bao cao). Tra ve lop de dung tiep."""
    clazz = db.get(models.Class, class_id)
    if not clazz:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lop hoc phan khong ton tai")
    if not can_view_class(user, clazz, db):
        raise _forbid("Khong co quyen voi lop hoc phan nay")
    return clazz


def filter_classes(query: Query, user: models.User, db: Session) -> Query:
    """Loc query da join models.Class theo pham vi xem cua user."""
    if user.role in SCHOOL_WIDE_VIEWERS:
        return query
    if user.role == ROLE_FACULTY:
        unit_id = staff_unit_id(user, db)
        return query.filter(models.Class.faculty_id == (unit_id if unit_id is not None else -1))
    if user.role == ROLE_LECTURER:
        lecturer = lecturer_profile(user, db)
        return query.filter(models.Class.lecturer_id == (lecturer.id if lecturer else -1))
    return query.filter(false())


# ---------------- Sinh vien ----------------

def can_view_student(user: models.User, student: models.Student, db: Session) -> bool:
    if user.role in SCHOOL_WIDE_VIEWERS:
        return True
    if user.role == ROLE_FACULTY:
        unit_id = staff_unit_id(user, db)
        return unit_id is not None and student.faculty_id == unit_id
    if user.role == ROLE_LECTURER:
        lecturer = lecturer_profile(user, db)
        if not lecturer:
            return False
        return (
            db.query(models.Enrollment)
            .join(models.Class, models.Class.id == models.Enrollment.class_id)
            .filter(models.Enrollment.student_id == student.id,
                    models.Class.lecturer_id == lecturer.id)
            .first()
        ) is not None
    if user.role == ROLE_STUDENT:
        return student.user_id == user.id
    if user.role == ROLE_PARENT:
        parent = db.query(models.Parent).filter_by(user_id=user.id).first()
        return parent is not None and (
            db.query(models.ParentStudent)
            .filter_by(parent_id=parent.id, student_id=student.id)
            .first()
        ) is not None
    return False


def ensure_student_view(user: models.User, student_id: int, db: Session) -> models.Student:
    student = db.get(models.Student, student_id)
    if not student:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sinh vien khong ton tai")
    if not can_view_student(user, student, db):
        raise _forbid("Khong co quyen voi sinh vien nay")
    return student


def filter_students(query: Query, user: models.User, db: Session) -> Query:
    """Loc query tren models.Student theo pham vi xem cua user."""
    if user.role in SCHOOL_WIDE_VIEWERS:
        return query
    if user.role == ROLE_FACULTY:
        unit_id = staff_unit_id(user, db)
        return query.filter(models.Student.faculty_id == (unit_id if unit_id is not None else -1))
    if user.role == ROLE_LECTURER:
        lecturer = lecturer_profile(user, db)
        taught = (
            db.query(models.Enrollment.student_id)
            .join(models.Class, models.Class.id == models.Enrollment.class_id)
            .filter(models.Class.lecturer_id == (lecturer.id if lecturer else -1))
        )
        return query.filter(models.Student.id.in_(taught))
    return query.filter(false())


# ---------------- Giang vien ----------------

def filter_lecturers(query: Query, user: models.User, db: Session) -> Query:
    if user.role in ACADEMIC_MANAGERS:
        return query
    if user.role == ROLE_FACULTY:
        unit_id = staff_unit_id(user, db)
        return query.filter(models.Lecturer.faculty_id == (unit_id if unit_id is not None else -1))
    return query.filter(false())


# ---------------- Diem danh ----------------

def can_excuse_record(user: models.User, record: models.AttendanceRecord, db: Session) -> bool:
    """P.CTSV duyet co phep toan truong; Khoa duyet cho SV thuoc Khoa hoac lop Khoa quan ly."""
    if user.role in (ROLE_ADMIN, ROLE_AFFAIRS):
        return True
    if user.role == ROLE_FACULTY:
        unit_id = staff_unit_id(user, db)
        if unit_id is None:
            return False
        clazz = record.session.schedule.clazz
        return record.student.faculty_id == unit_id or clazz.faculty_id == unit_id
    return False


def validate_faculty_id(db: Session, faculty_id: int | None) -> None:
    """faculty_id (neu co) phai la 1 don vi loai Khoa."""
    if faculty_id is None:
        return
    unit = db.get(models.Unit, faculty_id)
    if not unit or unit.type != models.UNIT_FACULTY:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Khoa khong hop le")
