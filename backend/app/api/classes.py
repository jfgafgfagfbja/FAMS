from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app import schemas
from app.core.security import get_current_user, require_roles
from app.db import models
from app.db.database import get_db

router = APIRouter(prefix="/classes", tags=["classes"])


def _get_class_or_404(db: Session, class_id: int) -> models.Class:
    clazz = db.get(models.Class, class_id)
    if not clazz:
        raise HTTPException(404, "Lop hoc phan khong ton tai")
    return clazz


@router.post("", response_model=schemas.ClassOut,
             dependencies=[Depends(require_roles("admin"))])
def create_class(body: schemas.ClassCreate, db: Session = Depends(get_db)):
    clazz = models.Class(**body.model_dump())
    db.add(clazz)
    db.commit()
    db.refresh(clazz)
    return clazz


@router.get("", response_model=list[schemas.ClassOut])
def list_classes(
    response: Response,
    mine: bool = False,
    q: str | None = None,
    limit: int | None = None,
    offset: int = 0,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """mine=true: giang vien chi thay lop minh day (admin/khac khong bi anh huong).
    q loc theo ma lop/ten mon, limit/offset phan trang - khong truyen limit thi tra
    ve toan bo nhu truoc (giu tuong thich cac noi dang dung danh sach day du, vd
    dropdown chon lop). Tong so ban ghi tra qua header X-Total-Count."""
    query = db.query(models.Class)
    if mine and user.role == "lecturer":
        lecturer = db.query(models.Lecturer).filter_by(user_id=user.id).first()
        query = query.filter(models.Class.lecturer_id == (lecturer.id if lecturer else -1))
    if q:
        like = f"%{q}%"
        query = query.filter(or_(models.Class.class_code.ilike(like),
                                 models.Class.subject_name.ilike(like)))

    response.headers["X-Total-Count"] = str(query.count())
    query = query.order_by(models.Class.class_code).offset(offset)
    if limit is not None:
        query = query.limit(limit)
    return query.all()


@router.get("/{class_id}", response_model=schemas.ClassOut)
def get_class(class_id: int, db: Session = Depends(get_db),
              _user: models.User = Depends(get_current_user)):
    """Chi tiet 1 lop hoc phan - dung cho trang /admin/classes/{id} (mo truc tiep
    qua URL/refresh, khong the dua vao danh sach da tai trong bo nho nhu truoc)."""
    return _get_class_or_404(db, class_id)


@router.patch("/{class_id}", response_model=schemas.ClassOut,
              dependencies=[Depends(require_roles("admin"))])
def update_class(class_id: int, body: schemas.ClassUpdate, db: Session = Depends(get_db)):
    clazz = _get_class_or_404(db, class_id)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(clazz, field, value)
    db.commit()
    db.refresh(clazz)
    return clazz


@router.delete("/{class_id}", dependencies=[Depends(require_roles("admin"))])
def delete_class(class_id: int, db: Session = Depends(get_db)):
    clazz = _get_class_or_404(db, class_id)
    if db.query(models.Enrollment).filter_by(class_id=class_id).first():
        raise HTTPException(409, "Lop hoc phan da co sinh vien ghi danh, khong the xoa truc tiep")
    if db.query(models.Schedule).filter_by(class_id=class_id).first():
        raise HTTPException(409, "Lop hoc phan da co lich hoc, hay xoa lich hoc truoc")
    db.delete(clazz)
    db.commit()
    return {"ok": True}


@router.post("/{class_id}/enroll/{student_id}",
             dependencies=[Depends(require_roles("admin"))])
def enroll_student(class_id: int, student_id: int, db: Session = Depends(get_db)):
    if db.query(models.Enrollment).filter_by(class_id=class_id, student_id=student_id).first():
        raise HTTPException(400, "Sinh vien da ghi danh lop nay")
    db.add(models.Enrollment(class_id=class_id, student_id=student_id))
    db.commit()
    return {"ok": True}


@router.delete("/{class_id}/enroll/{student_id}",
               dependencies=[Depends(require_roles("admin"))])
def unenroll_student(class_id: int, student_id: int, db: Session = Depends(get_db)):
    enrollment = db.query(models.Enrollment).filter_by(
        class_id=class_id, student_id=student_id).first()
    if not enrollment:
        raise HTTPException(404, "Sinh vien chua ghi danh lop nay")
    db.delete(enrollment)
    db.commit()
    return {"ok": True}


@router.get("/{class_id}/students", response_model=list[schemas.StudentOut],
            dependencies=[Depends(require_roles("admin", "lecturer"))])
def list_class_students(class_id: int, db: Session = Depends(get_db)):
    students = (
        db.query(models.Student)
        .join(models.Enrollment, models.Enrollment.student_id == models.Student.id)
        .filter(models.Enrollment.class_id == class_id)
        .all()
    )
    return [
        schemas.StudentOut(
            id=s.id, student_code=s.student_code, full_name=s.user.full_name,
            major=s.major, cohort=s.cohort, face_enrolled=len(s.embeddings) > 0,
            consent_given=s.consent_given,
        )
        for s in students
    ]


@router.get("/{class_id}/schedules", response_model=list[schemas.ScheduleOut])
def list_class_schedules(class_id: int, db: Session = Depends(get_db),
                         _user: models.User = Depends(get_current_user)):
    return db.query(models.Schedule).filter_by(class_id=class_id).all()


@router.post("/schedules", response_model=schemas.ScheduleOut,
             dependencies=[Depends(require_roles("admin"))])
def create_schedule(body: schemas.ScheduleCreate, db: Session = Depends(get_db)):
    sched = models.Schedule(**body.model_dump())
    db.add(sched)
    db.commit()
    db.refresh(sched)
    return sched


@router.patch("/schedules/{schedule_id}", response_model=schemas.ScheduleOut,
              dependencies=[Depends(require_roles("admin"))])
def update_schedule(schedule_id: int, body: schemas.ScheduleUpdate, db: Session = Depends(get_db)):
    sched = db.get(models.Schedule, schedule_id)
    if not sched:
        raise HTTPException(404, "Lich hoc khong ton tai")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(sched, field, value)
    db.commit()
    db.refresh(sched)
    return sched


@router.delete("/schedules/{schedule_id}", dependencies=[Depends(require_roles("admin"))])
def delete_schedule(schedule_id: int, db: Session = Depends(get_db)):
    sched = db.get(models.Schedule, schedule_id)
    if not sched:
        raise HTTPException(404, "Lich hoc khong ton tai")
    if db.query(models.AttendanceSession).filter_by(schedule_id=schedule_id).first():
        raise HTTPException(
            409, "Lich hoc da co phien diem danh, khong the xoa truc tiep")
    db.delete(sched)
    db.commit()
    return {"ok": True}
