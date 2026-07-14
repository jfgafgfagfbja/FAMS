from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import schemas
from app.core.security import get_current_user, hash_password, require_roles
from app.db import models
from app.db.database import get_db

router = APIRouter(prefix="/students", tags=["students"])


def _get_student_or_404(db: Session, student_id: int) -> models.Student:
    student = db.get(models.Student, student_id)
    if not student:
        raise HTTPException(404, "Sinh vien khong ton tai")
    return student


@router.post("", response_model=schemas.StudentOut,
             dependencies=[Depends(require_roles("admin"))])
def create_student(body: schemas.StudentCreate, db: Session = Depends(get_db)):
    if db.query(models.User).filter(models.User.email == body.email).first():
        raise HTTPException(400, "Email da ton tai")
    user = models.User(email=body.email, password_hash=hash_password(body.password),
                       role="student", full_name=body.full_name)
    db.add(user)
    db.flush()
    student = models.Student(user_id=user.id, student_code=body.student_code,
                             major=body.major, cohort=body.cohort)
    db.add(student)
    db.commit()
    db.refresh(student)
    return _to_out(student)


@router.get("", response_model=list[schemas.StudentOut],
            dependencies=[Depends(require_roles("admin", "lecturer"))])
def list_students(db: Session = Depends(get_db)):
    return [_to_out(s) for s in db.query(models.Student).all()]


@router.get("/me", response_model=schemas.StudentOut)
def get_my_student_record(
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    if user.role != "student":
        raise HTTPException(403, "Chi sinh vien moi co ho so nay")
    student = db.query(models.Student).filter_by(user_id=user.id).first()
    if not student:
        raise HTTPException(404, "Khong tim thay ho so sinh vien")
    return _to_out(student)


@router.get("/{student_id}", response_model=schemas.StudentOut,
            dependencies=[Depends(require_roles("admin", "lecturer"))])
def get_student(student_id: int, db: Session = Depends(get_db)):
    return _to_out(_get_student_or_404(db, student_id))


@router.patch("/{student_id}", response_model=schemas.StudentOut,
              dependencies=[Depends(require_roles("admin"))])
def update_student(student_id: int, body: schemas.StudentUpdate, db: Session = Depends(get_db)):
    student = _get_student_or_404(db, student_id)
    data = body.model_dump(exclude_unset=True)
    if "full_name" in data:
        student.user.full_name = data.pop("full_name")
    for field, value in data.items():
        setattr(student, field, value)
    db.commit()
    db.refresh(student)
    return _to_out(student)


@router.delete("/{student_id}", dependencies=[Depends(require_roles("admin"))])
def delete_student(student_id: int, db: Session = Depends(get_db)):
    student = _get_student_or_404(db, student_id)
    if student.enrollments or student.embeddings:
        raise HTTPException(
            409, "Sinh vien da co du lieu dang ky lop/khuon mat, khong the xoa truc tiep")
    user = student.user
    db.delete(student)
    db.delete(user)
    db.commit()
    return {"ok": True}


@router.post("/{student_id}/consent")
def give_consent(
    student_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """Xac nhan dong y cho phep thu thap du lieu khuon mat. Chi admin hoac chinh SV do."""
    student = _get_student_or_404(db, student_id)
    is_self = user.role == "student" and student.user_id == user.id
    if not is_self and user.role != "admin":
        raise HTTPException(403, "Chi sinh vien hoac admin moi xac nhan duoc dong y")
    student.consent_given = True
    student.consent_given_at = datetime.now()
    db.commit()
    return {"ok": True, "consent_given": True}


def _to_out(s: models.Student) -> schemas.StudentOut:
    return schemas.StudentOut(
        id=s.id, student_code=s.student_code, full_name=s.user.full_name,
        major=s.major, cohort=s.cohort, face_enrolled=len(s.embeddings) > 0,
        consent_given=s.consent_given,
    )
