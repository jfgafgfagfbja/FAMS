from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app import schemas
from app.api.schedules import open_from_time
from app.api.serializers import (delete_user_auth_rows, ensure_email_available,
                                 ensure_no_audit_history, lecturer_out)
from app.core.authz import ACADEMIC_MANAGERS, filter_lecturers, validate_faculty_id
from app.core.security import get_current_user, hash_password, require_roles
from app.db import models
from app.db.database import get_db
from app.db.models import FACULTY_ROLES, ROLE_ADMIN, ROLE_LECTURER, ROLE_TRAINING

router = APIRouter(prefix="/lecturers", tags=["lecturers"])

LECTURER_LIST_VIEWERS = (ROLE_ADMIN, ROLE_TRAINING, *FACULTY_ROLES)


def _get_lecturer_or_404(db: Session, lecturer_id: int) -> models.Lecturer:
    lecturer = db.get(models.Lecturer, lecturer_id)
    if not lecturer:
        raise HTTPException(404, "Giang vien khong ton tai")
    return lecturer


@router.post("", response_model=schemas.LecturerOut)
def create_lecturer(
    body: schemas.LecturerCreate,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_roles(*ACADEMIC_MANAGERS)),
):
    ensure_email_available(db, body.email)
    if db.query(models.Lecturer).filter_by(lecturer_code=body.lecturer_code).first():
        raise HTTPException(400, "Ma giang vien da ton tai")
    validate_faculty_id(db, body.faculty_id)

    user = models.User(email=body.email, password_hash=hash_password(body.password),
                       role=ROLE_LECTURER, full_name=body.full_name)
    db.add(user)
    db.flush()
    lecturer = models.Lecturer(user_id=user.id, lecturer_code=body.lecturer_code,
                               department=body.department, faculty_id=body.faculty_id)
    db.add(lecturer)
    db.commit()
    db.refresh(lecturer)
    return lecturer_out(lecturer)


@router.get("", response_model=list[schemas.LecturerOut])
def list_lecturers(
    response: Response,
    q: str | None = None,
    faculty_id: int | None = None,
    limit: int | None = None,
    offset: int = 0,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles(*LECTURER_LIST_VIEWERS)),
):
    """q loc theo ma GV/ho ten, limit/offset phan trang - khong truyen limit thi
    tra ve toan bo (vd dropdown chon giang vien khi tao lop). Can bo Khoa chi thay GV
    thuoc Khoa minh. Tong so ban ghi tra qua header X-Total-Count."""
    query = db.query(models.Lecturer).join(models.User, models.Lecturer.user_id == models.User.id)
    query = filter_lecturers(query, user, db)
    if q:
        like = f"%{q}%"
        query = query.filter(or_(models.Lecturer.lecturer_code.ilike(like),
                                 models.User.full_name.ilike(like)))
    if faculty_id is not None:
        query = query.filter(models.Lecturer.faculty_id == faculty_id)

    response.headers["X-Total-Count"] = str(query.count())
    query = query.order_by(models.Lecturer.lecturer_code).offset(offset)
    if limit is not None:
        query = query.limit(limit)
    return [lecturer_out(l) for l in query.all()]


@router.patch("/{lecturer_id}", response_model=schemas.LecturerOut)
def update_lecturer(
    lecturer_id: int,
    body: schemas.LecturerUpdate,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_roles(*ACADEMIC_MANAGERS)),
):
    lecturer = _get_lecturer_or_404(db, lecturer_id)
    data = body.model_dump(exclude_unset=True)
    if "faculty_id" in data:
        validate_faculty_id(db, data["faculty_id"])
    if "full_name" in data:
        lecturer.user.full_name = data.pop("full_name")
    for field, value in data.items():
        setattr(lecturer, field, value)
    db.commit()
    db.refresh(lecturer)
    return lecturer_out(lecturer)


@router.delete("/{lecturer_id}")
def delete_lecturer(
    lecturer_id: int,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_roles(*ACADEMIC_MANAGERS)),
):
    lecturer = _get_lecturer_or_404(db, lecturer_id)
    if db.query(models.Class).filter_by(lecturer_id=lecturer_id).first():
        raise HTTPException(
            409, "Giang vien dang phu trach lop hoc phan, khong the xoa truc tiep")
    user = lecturer.user
    ensure_no_audit_history(db, user.id)
    delete_user_auth_rows(db, user.id)
    db.delete(lecturer)
    db.delete(user)
    db.commit()
    return {"ok": True}


@router.get("/me/today-schedules", response_model=list[schemas.TodayScheduleOut])
def my_today_schedules(
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """Lich day hom nay cua giang vien dang dang nhap, kem phien da mo hom nay (neu co)
    de FE vao thang phien thay vi bam mo lai. Quy uoc weekday 0=thu 2 trung voi
    datetime.weekday() cua Python nen khong can quy doi nhu phia JS."""
    if user.role != ROLE_LECTURER:
        raise HTTPException(403, "Chi giang vien moi xem duoc lich day")
    lecturer = db.query(models.Lecturer).filter_by(user_id=user.id).first()
    if not lecturer:
        raise HTTPException(404, "Khong tim thay ho so giang vien")

    today: date = datetime.now().date()
    schedules = (
        db.query(models.Schedule)
        .join(models.Class)
        .filter(models.Class.lecturer_id == lecturer.id,
                models.Schedule.weekday == today.weekday())
        .order_by(models.Schedule.start_time)
        .all()
    )
    sessions = {}
    if schedules:
        sessions = {
            s.schedule_id: s
            for s in db.query(models.AttendanceSession)
            .filter(models.AttendanceSession.schedule_id.in_([s.id for s in schedules]),
                    models.AttendanceSession.session_date == today)
            .all()
        }
    return [
        schemas.TodayScheduleOut(
            schedule_id=s.id, class_id=s.class_id, class_code=s.clazz.class_code,
            subject_name=s.clazz.subject_name, weekday=s.weekday,
            start_time=s.start_time, end_time=s.end_time, room=s.room,
            open_from=open_from_time(s.start_time),
            session_id=sessions[s.id].id if s.id in sessions else None,
            session_status=sessions[s.id].status if s.id in sessions else None,
        )
        for s in schedules
    ]
