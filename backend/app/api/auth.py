import logging
import secrets
import time
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from app import schemas
from app.api.serializers import face_status_of
from app.core.authz import staff_profile
from app.core.config import settings
from app.core.security import (create_access_token, create_refresh_token, get_current_user,
                               hash_password, revoke_all_refresh_tokens, revoke_refresh_token,
                               revoke_token, rotate_refresh_token, verify_password)
from app.db import models
from app.db.database import get_db
from app.db.models import ROLE_LECTURER, ROLE_STUDENT, STAFF_ROLES
from app.services import email_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])
limiter = Limiter(key_func=get_remote_address)

# Dem so lan dang nhap sai theo tung tai khoan (in-memory, 1 process). Bo sung cho gioi
# han theo IP: SV dung chung wifi truong/4G co chung IP, neu chi gioi han theo IP thi ca
# lop bi khoa; nguoc lai ke do mat khau doi IP lien tuc van bi chan theo tai khoan.
_failed_logins: dict[str, list[float]] = {}
_MAX_TRACKED_ACCOUNTS = 10_000


def reset_login_failures() -> None:
    _failed_logins.clear()


def _recent_failures(key: str) -> list[float]:
    window = settings.LOGIN_FAILED_WINDOW_MINUTES * 60
    now = time.monotonic()
    attempts = [t for t in _failed_logins.get(key, []) if now - t < window]
    if attempts:
        _failed_logins[key] = attempts
    else:
        _failed_logins.pop(key, None)
    return attempts


def _record_failure(key: str) -> None:
    if len(_failed_logins) > _MAX_TRACKED_ACCOUNTS:
        for k in list(_failed_logins):
            _recent_failures(k)
    _failed_logins.setdefault(key, []).append(time.monotonic())


def _issue_tokens(db: Session, user: models.User) -> schemas.Token:
    return schemas.Token(
        access_token=create_access_token(user.id, user.role, user.token_version), role=user.role,
        refresh_token=create_refresh_token(db, user.id),
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/login", response_model=schemas.Token)
@limiter.limit(settings.LOGIN_RATE_LIMIT)
def login(
    request: Request,
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    key = form.username.strip().lower()
    if len(_recent_failures(key)) >= settings.LOGIN_MAX_FAILED_PER_ACCOUNT:
        raise HTTPException(
            429, "Dang nhap sai qua nhieu lan, vui long thu lai sau "
                 f"{settings.LOGIN_FAILED_WINDOW_MINUTES} phut")

    user = db.query(models.User).filter(models.User.email == form.username).first()
    if not user or not verify_password(form.password, user.password_hash):
        _record_failure(key)
        raise HTTPException(401, "Sai email hoac mat khau")

    _failed_logins.pop(key, None)
    return _issue_tokens(db, user)


@router.post("/refresh", response_model=schemas.Token)
@limiter.limit("60/minute")
def refresh(
    request: Request,
    body: schemas.RefreshRequest,
    db: Session = Depends(get_db),
):
    """Doi refresh token lay cap token moi (refresh token cu bi thu hoi - xoay vong)."""
    user, new_refresh = rotate_refresh_token(db, body.refresh_token)
    return schemas.Token(
        access_token=create_access_token(user.id, user.role, user.token_version), role=user.role,
        refresh_token=new_refresh, expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
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

    try:
        email_service.send_otp_email(user.email, otp)
    except Exception:
        # Van tra thong bao chung: tra 500 o day se lo ra email nay CO ton tai.
        logger.exception("Gui email OTP that bai")
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
    token_version (xem core/security.py::get_current_user) va refresh token."""
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
    user.token_version = (user.token_version or 0) + 1
    revoke_all_refresh_tokens(db, user.id)
    db.commit()
    return {"ok": True}


@router.post("/change-password", response_model=schemas.Token)
@limiter.limit("10/minute")
def change_password(
    request: Request,
    body: schemas.ChangePasswordRequest,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """Nguoi dang dang nhap tu doi mat khau.

    Phai nhap dung mat khau hien tai: ai do ngoi vao may dang mo san phien dang nhap cung
    khong doi duoc mat khau de chiem tai khoan. Nhap sai nhieu lan thi bi tam khoa giong
    dang nhap. Doi xong thu hoi moi phien khac (may khac, trinh duyet khac) - de phong
    truong hop doi vi nghi bi lo mat khau - va cap token moi cho chinh phien nay de nguoi
    dung khong bi dang xuat giua chung.
    """
    key = f"change-password:{user.id}"
    if len(_recent_failures(key)) >= settings.LOGIN_MAX_FAILED_PER_ACCOUNT:
        raise HTTPException(
            429, "Nhap sai mat khau qua nhieu lan, vui long thu lai sau "
                 f"{settings.LOGIN_FAILED_WINDOW_MINUTES} phut")

    if not verify_password(body.current_password, user.password_hash):
        _record_failure(key)
        raise HTTPException(400, "Mat khau hien tai khong dung")
    if verify_password(body.new_password, user.password_hash):
        raise HTTPException(400, "Mat khau moi phai khac mat khau hien tai")

    _failed_logins.pop(key, None)
    user.password_hash = hash_password(body.new_password)
    user.credentials_changed_at = datetime.utcnow()
    user.token_version = (user.token_version or 0) + 1
    revoke_all_refresh_tokens(db, user.id)
    db.commit()
    db.refresh(user)
    return _issue_tokens(db, user)


@router.post("/logout")
def logout(
    request: Request,
    body: schemas.LogoutRequest | None = None,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    revoke_token(db, request.state.token_payload)
    if body and body.refresh_token:
        revoke_refresh_token(db, body.refresh_token, user.id)
    return {"ok": True}


@router.get("/me", response_model=schemas.MeOut)
def get_me(
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """Thong tin tai khoan dang dang nhap, kem ho so: SV (lop da ghi danh), GV (lop dang
    day), can bo phong ban (don vi) - frontend dung de dieu huong va hien the ca nhan."""
    data = {"id": user.id, "email": user.email, "full_name": user.full_name, "role": user.role}

    if user.role == ROLE_STUDENT:
        student = db.query(models.Student).filter_by(user_id=user.id).first()
        if student:
            data.update(
                student_id=student.id, student_code=student.student_code, major=student.major,
                cohort=student.cohort, consent_given=student.consent_given,
                face_status=face_status_of(student),
                faculty_id=student.faculty_id,
                faculty_name=student.faculty.name if student.faculty else None,
                classes=[
                    schemas.MeClassBrief(
                        id=e.clazz.id, class_code=e.clazz.class_code,
                        subject_name=e.clazz.subject_name, semester=e.clazz.semester,
                    )
                    for e in student.enrollments
                ],
            )
    elif user.role == ROLE_LECTURER:
        lecturer = db.query(models.Lecturer).filter_by(user_id=user.id).first()
        if lecturer:
            classes = db.query(models.Class).filter_by(lecturer_id=lecturer.id).all()
            data.update(
                lecturer_id=lecturer.id, lecturer_code=lecturer.lecturer_code,
                department=lecturer.department, faculty_id=lecturer.faculty_id,
                faculty_name=lecturer.faculty.name if lecturer.faculty else None,
                classes=[
                    schemas.MeClassBrief(
                        id=c.id, class_code=c.class_code,
                        subject_name=c.subject_name, semester=c.semester,
                    )
                    for c in classes
                ],
            )
    elif user.role in STAFF_ROLES:
        staff = staff_profile(user, db)
        if staff:
            data.update(
                unit_id=staff.unit_id, unit_code=staff.unit.code, unit_name=staff.unit.name,
                unit_type=staff.unit.type, position=staff.position,
            )

    return schemas.MeOut(**data)
