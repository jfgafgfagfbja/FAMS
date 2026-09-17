import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from app import schemas
from app.core.config import settings
from app.core.security import (create_access_token, get_current_user, hash_password,
                               revoke_token, verify_password)
from app.db import models
from app.db.database import get_db
from app.services import email_service

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


@router.post("/forgot-password")
@limiter.limit("3/hour")
def forgot_password(
    request: Request,
    body: schemas.ForgotPasswordRequest,
    db: Session = Depends(get_db),
):
    """Gui ma OTP qua email de dat lai mat khau. Luon tra ve thong bao chung du
    email co ton tai hay khong, tranh lo thong tin tai khoan nao dang ton tai
    (chong do email). Gioi han chat 3 lan/gio/IP qua slowapi de chong spam."""
    generic_response = {
        "message": "Neu email ton tai trong he thong, ma OTP da duoc gui den email do.",
    }

    user = db.query(models.User).filter(models.User.email == body.email).first()
    if not user:
        return generic_response

    otp = f"{secrets.randbelow(1_000_000):06d}"
    db.add(models.PasswordReset(
        user_id=user.id, otp_hash=hash_password(otp),
        expires_at=datetime.utcnow() + timedelta(minutes=settings.OTP_EXPIRE_MINUTES),
    ))
    db.commit()

    email_service.send_otp_email(user.email, otp)
    return generic_response


@router.post("/reset-password")
@limiter.limit("10/hour")
def reset_password(
    request: Request,
    body: schemas.ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    """Dat lai mat khau bang OTP: kiem OTP dung + con han + chua dung (so voi
    TAT CA yeu cau con hieu luc, phong truong hop SV xin OTP nhieu lan). Doi mat
    khau xong thu hoi toan bo token dang hoat dong cua user qua
    credentials_changed_at (xem core/security.py::get_current_user)."""
    user = db.query(models.User).filter(models.User.email == body.email).first()
    if not user:
        raise HTTPException(400, "Thong tin dat lai mat khau khong hop le")

    candidates = (
        db.query(models.PasswordReset)
        .filter(models.PasswordReset.user_id == user.id,
                models.PasswordReset.used.is_(False),
                models.PasswordReset.expires_at >= datetime.utcnow())
        .all()
    )
    matched = next((r for r in candidates if verify_password(body.otp, r.otp_hash)), None)
    if not matched:
        raise HTTPException(400, "Ma OTP khong dung hoac da het han")

    matched.used = True
    user.password_hash = hash_password(body.new_password)
    user.credentials_changed_at = datetime.utcnow()
    db.commit()
    return {"ok": True}


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
