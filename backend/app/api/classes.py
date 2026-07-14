from fastapi import APIRouter, Depends, HTTPException
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
    mine: bool = False,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """mine=true: giang vien chi thay lop minh day (admin/khac khong bi anh huong)."""
    query = db.query(models.Class)
    if mine and user.role == "lecturer":
        lecturer = db.query(models.Lecturer).filter_by(user_id=user.id).first()
        query = query.filter(models.Class.lecturer_id == (lecturer.id if lecturer else -1))
    return query.all()


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


@router.delete("/schedules/{schedule_id}", dependencies=[Depends(require_roles("admin"))])
def delete_schedule(schedule_id: int, db: Session = Depends(get_db)):
    sched = db.get(models.Schedule, schedule_id)
    if not sched:
        raise HTTPException(404, "Lich hoc khong ton tai")
    db.delete(sched)
    db.commit()
    return {"ok": True}
