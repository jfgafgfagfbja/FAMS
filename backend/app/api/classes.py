from datetime import time

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app import schemas
from app.api.serializers import class_out, schedule_out, student_out
from app.core.authz import (CLASS_EDITORS, CLASS_VIEWERS, can_view_class,
                            ensure_class_manage, faculty_for_new_class,
                            ensure_class_view, filter_classes, validate_faculty_id)
from app.core.security import get_current_user, require_roles
from app.db import models
from app.db.database import get_db
from app.db.models import ROLE_STUDENT

router = APIRouter(prefix="/classes", tags=["classes"])


def _get_class_or_404(db: Session, class_id: int) -> models.Class:
    clazz = db.get(models.Class, class_id)
    if not clazz:
        raise HTTPException(404, "Lop hoc phan khong ton tai")
    return clazz


def _validate_lecturer(db: Session, lecturer_id: int) -> None:
    if not db.get(models.Lecturer, lecturer_id):
        raise HTTPException(400, "Giang vien khong ton tai")


def _ensure_class_code_available(db: Session, class_code: str, exclude_id: int | None = None) -> None:
    existed = db.query(models.Class).filter_by(class_code=class_code).first()
    if existed and existed.id != exclude_id:
        raise HTTPException(400, "Ma lop hoc phan da ton tai")


def _validate_location(db: Session, location_id: int | None) -> None:
    if location_id is not None and not db.get(models.Location, location_id):
        raise HTTPException(400, "Dia diem khong ton tai")


def _student_counts(db: Session, class_ids: list[int]) -> dict[int, int]:
    if not class_ids:
        return {}
    rows = (
        db.query(models.Enrollment.class_id, func.count())
        .filter(models.Enrollment.class_id.in_(class_ids))
        .group_by(models.Enrollment.class_id)
        .all()
    )
    return dict(rows)


@router.post("", response_model=schemas.ClassOut)
def create_class(
    body: schemas.ClassCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles(*CLASS_EDITORS)),
):
    _ensure_class_code_available(db, body.class_code)
    _validate_lecturer(db, body.lecturer_id)
    data = body.model_dump()
    data["faculty_id"] = faculty_for_new_class(user, db, data.get("faculty_id"))
    validate_faculty_id(db, data["faculty_id"])
    clazz = models.Class(**data)
    db.add(clazz)
    db.commit()
    db.refresh(clazz)
    return class_out(clazz, student_count=0)


@router.get("", response_model=list[schemas.ClassOut])
def list_classes(
    response: Response,
    mine: bool = False,
    q: str | None = None,
    semester: str | None = None,
    faculty_id: int | None = None,
    limit: int | None = None,
    offset: int = 0,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles(*CLASS_VIEWERS)),
):
    """Danh sach lop trong pham vi xem cua user: admin/P.DT/P.CTSV toan truong, Khoa chi
    lop Khoa quan ly, giang vien chi lop minh day (tham so mine giu de tuong thich).
    Loc theo q (ma lop/ten mon), semester, faculty_id; phan trang limit/offset, tong so
    ban ghi tra qua header X-Total-Count."""
    query = filter_classes(db.query(models.Class), user, db)
    if q:
        like = f"%{q}%"
        query = query.filter(or_(models.Class.class_code.ilike(like),
                                 models.Class.subject_name.ilike(like)))
    if semester:
        query = query.filter(models.Class.semester == semester)
    if faculty_id is not None:
        query = query.filter(models.Class.faculty_id == faculty_id)

    response.headers["X-Total-Count"] = str(query.count())
    query = query.order_by(models.Class.class_code).offset(offset)
    if limit is not None:
        query = query.limit(limit)
    classes = query.all()
    counts = _student_counts(db, [c.id for c in classes])
    return [class_out(c, student_count=counts.get(c.id, 0)) for c in classes]


@router.get("/{class_id}", response_model=schemas.ClassOut)
def get_class(class_id: int, db: Session = Depends(get_db),
              user: models.User = Depends(get_current_user)):
    clazz = ensure_class_view(user, class_id, db)
    return class_out(clazz, student_count=_student_counts(db, [clazz.id]).get(clazz.id, 0))


@router.patch("/{class_id}", response_model=schemas.ClassOut)
def update_class(
    class_id: int,
    body: schemas.ClassUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles(*CLASS_EDITORS)),
):
    clazz = _get_class_or_404(db, class_id)
    ensure_class_manage(user, clazz, db)
    data = body.model_dump(exclude_unset=True)
    if "faculty_id" in data:
        # Van phong Khoa khong chuyen lop sang Khoa khac.
        data["faculty_id"] = faculty_for_new_class(user, db, data["faculty_id"])
    if data.get("class_code"):
        _ensure_class_code_available(db, data["class_code"], exclude_id=class_id)
    if data.get("lecturer_id") is not None:
        _validate_lecturer(db, data["lecturer_id"])
    if "faculty_id" in data:
        validate_faculty_id(db, data["faculty_id"])
    for field, value in data.items():
        setattr(clazz, field, value)
    db.commit()
    db.refresh(clazz)
    return class_out(clazz)


@router.delete("/{class_id}")
def delete_class(
    class_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles(*CLASS_EDITORS)),
):
    clazz = _get_class_or_404(db, class_id)
    ensure_class_manage(user, clazz, db)
    if db.query(models.Enrollment).filter_by(class_id=class_id).first():
        raise HTTPException(409, "Lop hoc phan da co sinh vien ghi danh, khong the xoa truc tiep")
    if db.query(models.Schedule).filter_by(class_id=class_id).first():
        raise HTTPException(409, "Lop hoc phan da co lich hoc, hay xoa lich hoc truoc")
    db.delete(clazz)
    db.commit()
    return {"ok": True}


@router.post("/{class_id}/enroll/{student_id}")
def enroll_student(
    class_id: int,
    student_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles(*CLASS_EDITORS)),
):
    ensure_class_manage(user, _get_class_or_404(db, class_id), db)
    if not db.get(models.Student, student_id):
        raise HTTPException(404, "Sinh vien khong ton tai")
    if db.query(models.Enrollment).filter_by(class_id=class_id, student_id=student_id).first():
        raise HTTPException(400, "Sinh vien da ghi danh lop nay")
    db.add(models.Enrollment(class_id=class_id, student_id=student_id))
    db.commit()
    return {"ok": True}


@router.delete("/{class_id}/enroll/{student_id}")
def unenroll_student(
    class_id: int,
    student_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles(*CLASS_EDITORS)),
):
    ensure_class_manage(user, _get_class_or_404(db, class_id), db)
    enrollment = db.query(models.Enrollment).filter_by(
        class_id=class_id, student_id=student_id).first()
    if not enrollment:
        raise HTTPException(404, "Sinh vien chua ghi danh lop nay")
    db.delete(enrollment)
    db.commit()
    return {"ok": True}


@router.get("/{class_id}/students", response_model=list[schemas.StudentOut])
def list_class_students(class_id: int, db: Session = Depends(get_db),
                        user: models.User = Depends(get_current_user)):
    ensure_class_view(user, class_id, db)
    students = (
        db.query(models.Student)
        .join(models.Enrollment, models.Enrollment.student_id == models.Student.id)
        .filter(models.Enrollment.class_id == class_id)
        .order_by(models.Student.student_code)
        .all()
    )
    return [student_out(s) for s in students]


@router.get("/{class_id}/schedules", response_model=list[schemas.ScheduleOut])
def list_class_schedules(class_id: int, db: Session = Depends(get_db),
                         user: models.User = Depends(get_current_user)):
    """Lich hoc cua lop: nguoi xem duoc lop, hoac SV dang ghi danh lop do."""
    clazz = _get_class_or_404(db, class_id)
    allowed = can_view_class(user, clazz, db)
    if not allowed and user.role == ROLE_STUDENT:
        student = db.query(models.Student).filter_by(user_id=user.id).first()
        allowed = student is not None and db.query(models.Enrollment).filter_by(
            class_id=class_id, student_id=student.id).first() is not None
    if not allowed:
        raise HTTPException(403, "Khong co quyen voi lop hoc phan nay")
    rows = (db.query(models.Schedule).filter_by(class_id=class_id)
            .order_by(models.Schedule.weekday, models.Schedule.start_time).all())
    return [schedule_out(s) for s in rows]


def _validate_room(db: Session, room_id: int | None) -> models.Room | None:
    if room_id is None:
        return None
    room = db.get(models.Room, room_id)
    if not room:
        raise HTTPException(400, "Phong hoc khong ton tai")
    if not room.is_active:
        raise HTTPException(400, f"Phong {room.name} da ngung su dung, hay chon phong khac")
    return room


def _ensure_room_free(db: Session, room_id: int | None, weekday: int,
                      start: time, end: time, exclude_id: int | None = None) -> None:
    """Mot phong khong the chua 2 lop cung thu, trung khung gio - loi hay gap khi xep
    thoi khoa bieu. Hai tiet lien nhau (ket thuc = bat dau) van hop le."""
    if room_id is None:
        return
    query = (
        db.query(models.Schedule)
        .filter(models.Schedule.room_id == room_id,
                models.Schedule.weekday == weekday,
                models.Schedule.start_time < end,
                models.Schedule.end_time > start)
    )
    if exclude_id is not None:
        query = query.filter(models.Schedule.id != exclude_id)
    clash = query.first()
    if clash is None:
        return
    raise HTTPException(
        400,
        f"Phong nay da co lop {clash.clazz.class_code} hoc "
        f"{clash.start_time.strftime('%H:%M')}-{clash.end_time.strftime('%H:%M')} cung thu")


@router.post("/schedules", response_model=schemas.ScheduleOut)
def create_schedule(
    body: schemas.ScheduleCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles(*CLASS_EDITORS)),
):
    ensure_class_manage(user, _get_class_or_404(db, body.class_id), db)
    _validate_location(db, body.location_id)
    room = _validate_room(db, body.room_id)
    _ensure_room_free(db, body.room_id, body.weekday, body.start_time, body.end_time)
    data = body.model_dump()
    # Cot `room` dang chu luon co gia tri de du lieu cu va cho hien thi khong bi trong.
    data["room"] = (data.get("room") or "").strip() or (room.code if room else "")
    sched = models.Schedule(**data)
    db.add(sched)
    db.commit()
    db.refresh(sched)
    return schedule_out(sched)


@router.patch("/schedules/{schedule_id}", response_model=schemas.ScheduleOut)
def update_schedule(
    schedule_id: int,
    body: schemas.ScheduleUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles(*CLASS_EDITORS)),
):
    sched = db.get(models.Schedule, schedule_id)
    if not sched:
        raise HTTPException(404, "Lich hoc khong ton tai")
    ensure_class_manage(user, sched.clazz, db)
    data = body.model_dump(exclude_unset=True)
    if "location_id" in data:
        _validate_location(db, data["location_id"])
    room = _validate_room(db, data["room_id"]) if "room_id" in data else None
    start = data.get("start_time", sched.start_time)
    end = data.get("end_time", sched.end_time)
    if start is None or end is None or start >= end:
        raise HTTPException(400, "Gio bat dau phai truoc gio ket thuc")
    weekday = data.get("weekday", sched.weekday)
    _ensure_room_free(db, data.get("room_id", sched.room_id), weekday, start, end,
                      exclude_id=sched.id)
    if room is not None and not (data.get("room") or "").strip():
        data["room"] = room.code
    for field, value in data.items():
        setattr(sched, field, value)
    if not (sched.room or "").strip():
        raise HTTPException(400, "Phai chon phong hoc hoac nhap ten phong")
    db.commit()
    db.refresh(sched)
    return schedule_out(sched)


@router.delete("/schedules/{schedule_id}")
def delete_schedule(
    schedule_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles(*CLASS_EDITORS)),
):
    sched = db.get(models.Schedule, schedule_id)
    if not sched:
        raise HTTPException(404, "Lich hoc khong ton tai")
    ensure_class_manage(user, sched.clazz, db)
    if db.query(models.AttendanceSession).filter_by(schedule_id=schedule_id).first():
        raise HTTPException(
            409, "Lich hoc da co phien diem danh, khong the xoa truc tiep")
    db.delete(sched)
    db.commit()
    return {"ok": True}
