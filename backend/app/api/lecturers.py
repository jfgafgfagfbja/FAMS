from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import schemas
from app.core.security import hash_password, require_roles
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
def list_lecturers(db: Session = Depends(get_db)):
    return [_to_out(l) for l in db.query(models.Lecturer).all()]


def _to_out(l: models.Lecturer) -> schemas.LecturerOut:
    return schemas.LecturerOut(
        id=l.id, lecturer_code=l.lecturer_code, full_name=l.user.full_name,
        department=l.department,
    )
