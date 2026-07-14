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
def list_classes(db: Session = Depends(get_db), _user: models.User = Depends(get_current_user)):
    return db.query(models.Class).all()


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
    db.add(models.Enrollment(class_id=class_id, student_id=student_id))
    db.commit()
    return {"ok": True}


@router.post("/schedules", dependencies=[Depends(require_roles("admin"))])
def create_schedule(body: schemas.ScheduleCreate, db: Session = Depends(get_db)):
    sched = models.Schedule(**body.model_dump())
    db.add(sched)
    db.commit()
    return {"ok": True, "id": sched.id}
