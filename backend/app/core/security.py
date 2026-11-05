import hashlib
import secrets
import uuid
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import get_db
from app.db import models
from app.services.audit import set_actor

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(user_id: int, role: str, token_version: int = 0) -> str:
    now = datetime.utcnow()
    expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "role": role, "exp": expire, "iat": now,
               "jti": uuid.uuid4().hex, "tv": token_version}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def _decode(token: str) -> dict:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token khong hop le")


def get_current_user(
    request: Request,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    payload = _decode(token)
    try:
        user_id = int(payload["sub"])
        jti = payload["jti"]
    except (KeyError, ValueError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token khong hop le")

    if db.query(models.RevokedToken).filter_by(jti=jti).first():
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token da bi thu hoi, vui long dang nhap lai")

    user = db.get(models.User, user_id)
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User khong ton tai")

    # Token phat truoc lan doi mat khau gan nhat (vd qua quen mat khau) bi coi la
    # da thu hoi - khong the liet ke tung jti da phat truoc do nen so version: moi lan
    # dat lai mat khau tang users.token_version. Truoc day so "iat" voi moc thoi gian
    # nhung "iat" chi chinh xac toi giay, token phat CUNG GIAY voi luc doi mat khau van
    # song sot. Token khong co "tv" (phat truoc khi co co che nay) coi nhu version 0.
    if payload.get("tv", 0) != user.token_version:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Token da bi thu hoi do doi mat khau, vui long dang nhap lai")

    request.state.token_payload = payload
    # Moi thay doi du lieu trong request nay duoc ghi nhat ky dung ten nguoi nay (services/audit.py).
    set_actor(db, user, request)
    return user


def revoke_token(db: Session, payload: dict) -> None:
    """Ghi jti cua token hien tai vao blocklist (goi khi logout)."""
    jti = payload.get("jti")
    exp = payload.get("exp")
    if not jti or db.query(models.RevokedToken).filter_by(jti=jti).first():
        return
    db.add(models.RevokedToken(jti=jti, expires_at=datetime.utcfromtimestamp(exp)))
    db.commit()


# ---------------- Refresh token (app mobile) ----------------

def _hash_refresh_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def create_refresh_token(db: Session, user_id: int) -> str:
    raw = secrets.token_urlsafe(48)
    db.add(models.RefreshToken(
        user_id=user_id, token_hash=_hash_refresh_token(raw),
        expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    ))
    db.commit()
    return raw


def revoke_all_refresh_tokens(db: Session, user_id: int) -> None:
    (
        db.query(models.RefreshToken)
        .filter(models.RefreshToken.user_id == user_id, models.RefreshToken.revoked_at.is_(None))
        .update({"revoked_at": datetime.utcnow()})
    )


def revoke_refresh_token(db: Session, raw: str, user_id: int) -> None:
    """Thu hoi 1 refresh token (logout) - chi token thuoc chinh user dang dang xuat."""
    token = db.query(models.RefreshToken).filter_by(token_hash=_hash_refresh_token(raw)).first()
    if token and token.user_id == user_id and token.revoked_at is None:
        token.revoked_at = datetime.utcnow()
        db.commit()


def rotate_refresh_token(db: Session, raw: str) -> tuple[models.User, str]:
    """Doi refresh token cu lay (user, refresh token moi). Token cu bi thu hoi."""
    invalid = HTTPException(status.HTTP_401_UNAUTHORIZED, "Phien dang nhap het han, vui long dang nhap lai")
    token = db.query(models.RefreshToken).filter_by(token_hash=_hash_refresh_token(raw)).first()
    if not token:
        raise invalid
    if token.revoked_at is not None:
        # Token da xoay vong/thu hoi ma van bi dung lai -> co the da bi lo: thu hoi het.
        revoke_all_refresh_tokens(db, token.user_id)
        db.commit()
        raise invalid
    if token.expires_at < datetime.utcnow():
        raise invalid

    user = db.get(models.User, token.user_id)
    if not user:
        raise invalid
    token.revoked_at = datetime.utcnow()
    db.commit()
    return user, create_refresh_token(db, user.id)


def require_roles(*roles: str):
    def checker(user: models.User = Depends(get_current_user)) -> models.User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Khong du quyen")
        return user

    return checker
