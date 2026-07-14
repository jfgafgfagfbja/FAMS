from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from app import schemas
from app.core.security import create_access_token, get_current_user, revoke_token, verify_password
from app.db import models
from app.db.database import get_db

router = APIRouter(prefix="/auth", tags=["auth"])
limiter = Limiter(key_func=get_remote_address)


@router.post("/login", response_model=schemas.Token)
@limiter.limit("5/minute")
def login(
    request: Request,
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.email == form.username).first()
    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(401, "Sai email hoac mat khau")
    return schemas.Token(
        access_token=create_access_token(user.id, user.role), role=user.role
    )


@router.post("/logout")
def logout(
    request: Request,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    revoke_token(db, request.state.token_payload)
    return {"ok": True}


@router.get("/me", response_model=schemas.MeOut)
def get_me(
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """Thong tin tai khoan dang dang nhap, kem ho so va danh sach lop (SV: da ghi danh,
    GV: dang day) - frontend dung cho the thong tin ca nhan va trang lich hoc."""
    data = {"id": user.id, "email": user.email, "full_name": user.full_name, "role": user.role}

    if user.role == "student":
        student = db.query(models.Student).filter_by(user_id=user.id).first()
        if student:
            data.update(
                student_code=student.student_code, major=student.major,
                cohort=student.cohort, consent_given=student.consent_given,
                classes=[
                    schemas.MeClassBrief(
                        id=e.clazz.id, class_code=e.clazz.class_code,
                        subject_name=e.clazz.subject_name, semester=e.clazz.semester,
                    )
                    for e in student.enrollments
                ],
            )
    elif user.role == "lecturer":
        lecturer = db.query(models.Lecturer).filter_by(user_id=user.id).first()
        if lecturer:
            classes = db.query(models.Class).filter_by(lecturer_id=lecturer.id).all()
            data.update(
                lecturer_code=lecturer.lecturer_code, department=lecturer.department,
                classes=[
                    schemas.MeClassBrief(
                        id=c.id, class_code=c.class_code,
                        subject_name=c.subject_name, semester=c.semester,
                    )
                    for c in classes
                ],
            )

    return schemas.MeOut(**data)
