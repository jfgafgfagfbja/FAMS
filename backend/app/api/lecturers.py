from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app import schemas
from app.api.schedules import open_from_time
from app.core.security import get_current_user, hash_password, require_roles
from app.db import models
from app.db.database import get_db

router = APIRouter(prefix="/lecturers", tags=["lecturers"])


@router.post("", response_model=schemas.LecturerOut,
             dependencies=[Depends(require_roles("admin"))])
def create_lecturer(body: schemas.LecturerCreate, db: Session = Depends(get_db)):
    if db.query(models.User).filter(models.User.email == body.email).first():
        raise HTTPException(400, "Email da ton tai")
    user = models.User(email=body.email, password_hash=hash_password(body.password),
                       role="lecturer", full_name=body.full_name)
    db.add(user)
    db.flush()
    lecturer = models.Lecturer(user_id=user.id, lecturer_code=body.lecturer_code,
                               department=body.department)
    db.add(lecturer)
    db.commit()
    db.refresh(lecturer)
    return _to_out(lecturer)


@router.get("", response_model=list[schemas.LecturerOut],
            dependencies=[Depends(require_roles("admin"))])
def list_lecturers(
    response: Response,
    q: str | None = None,
    limit: int | None = None,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """q loc theo ma GV/ho ten, limit/offset phan trang - khong truyen limit thi
    tra ve toan bo (giu tuong thich cac noi dang dung danh sach day du, vd dropdown
    chon giang vien khi tao lop). Tong so ban ghi tra qua header X-Total-Count."""
    query = db.query(models.Lecturer).join(models.User, models.Lecturer.user_id == models.User.id)
    if q:
        like = f"%{q}%"
        query = query.filter(or_(models.Lecturer.lecturer_code.ilike(like),
                                 models.User.full_name.ilike(like)))

    response.headers["X-Total-Count"] = str(query.count())
    query = query.order_by(models.Lecturer.lecturer_code).offset(offset)
    if limit is not None:
        query = query.limit(limit)
    return [_to_out(l) for l in query.all()]


@router.patch("/{lecturer_id}", response_model=schemas.LecturerOut,
              dependencies=[Depends(require_roles("admin"))])
def update_lecturer(lecturer_id: int, body: schemas.LecturerUpdate, db: Session = Depends(get_db)):
    lecturer = db.get(models.Lecturer, lecturer_id)
    if not lecturer:
        raise HTTPException(404, "Giang vien khong ton tai")
    data = body.model_dump(exclude_unset=True)
    if "full_name" in data:
        lecturer.user.full_name = data.pop("full_name")
    for field, value in data.items():
        setattr(lecturer, field, value)
    db.commit()
    db.refresh(lecturer)
    return _to_out(lecturer)


@router.delete("/{lecturer_id}", dependencies=[Depends(require_roles("admin"))])
def delete_lecturer(lecturer_id: int, db: Session = Depends(get_db)):
    lecturer = db.get(models.Lecturer, lecturer_id)
    if not lecturer:
        raise HTTPException(404, "Giang vien khong ton tai")
    if db.query(models.Class).filter_by(lecturer_id=lecturer_id).first():
        raise HTTPException(
            409, "Giang vien dang phu trach lop hoc phan, khong the xoa truc tiep")
    user = lecturer.user
    db.delete(lecturer)
    db.delete(user)
    db.commit()
    return {"ok": True}


@router.get("/me/today-schedules", response_model=list[schemas.TodayScheduleOut])
def my_today_schedules(
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """Lich day hom nay cua giang vien dang dang nhap. Quy uoc weekday 0=thu 2 trung
    voi datetime.weekday() cua Python nen khong can quy doi nhu phia JS."""
    if user.role != "lecturer":
        raise HTTPException(403, "Chi giang vien moi xem duoc lich day")
    lecturer = db.query(models.Lecturer).filter_by(user_id=user.id).first()
    if not lecturer:
        raise HTTPException(404, "Khong tim thay ho so giang vien")

    today_weekday = datetime.now().weekday()
    schedules = (
        db.query(models.Schedule)
        .join(models.Class)
        .filter(models.Class.lecturer_id == lecturer.id,
                models.Schedule.weekday == today_weekday)
        .all()
    )
    return [
        schemas.TodayScheduleOut(
            schedule_id=s.id, class_id=s.class_id, class_code=s.clazz.class_code,
            subject_name=s.clazz.subject_name, weekday=s.weekday,
            start_time=s.start_time, end_time=s.end_time, room=s.room,
            open_from=open_from_time(s.start_time),
        )
        for s in schedules
    ]


def _to_out(l: models.Lecturer) -> schemas.LecturerOut:
    return schemas.LecturerOut(
        id=l.id, lecturer_code=l.lecturer_code, full_name=l.user.full_name,
        department=l.department,
    )
