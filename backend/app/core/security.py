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

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(user_id: int, role: str) -> str:
    now = datetime.utcnow()
    expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "role": role, "exp": expire, "iat": now, "jti": uuid.uuid4().hex}
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
    # da thu hoi - khong the liet ke tung jti da phat truoc do nen dung moc thoi
    # gian de thu hoi hang loat. Token cu (phat truoc khi co tinh nang nay) khong
    # co "iat" nen bo qua kiem tra, khong lam gian doan phien dang dang nhap.
    iat = payload.get("iat")
    if user.credentials_changed_at and iat is not None:
        issued_at = datetime.utcfromtimestamp(iat)
        # So sanh o do phan giai GIAY: "iat" trong JWT bi lam tron xuong giay chan,
        # con credentials_changed_at co microsecond - neu giu nguyen thi token phat
        # ra NGAY SAU khi doi mat khau (cung giay) cung bi coi la cu va tra 401 oan.
        if issued_at < user.credentials_changed_at.replace(microsecond=0):
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED,
                "Token da bi thu hoi do doi mat khau, vui long dang nhap lai")

    request.state.token_payload = payload
    return user


def revoke_token(db: Session, payload: dict) -> None:
    """Ghi jti cua token hien tai vao blocklist (goi khi logout)."""
    jti = payload.get("jti")
    exp = payload.get("exp")
    if not jti or db.query(models.RevokedToken).filter_by(jti=jti).first():
        return
    db.add(models.RevokedToken(jti=jti, expires_at=datetime.utcfromtimestamp(exp)))
    db.commit()


def require_roles(*roles: str):
    def checker(user: models.User = Depends(get_current_user)) -> models.User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Khong du quyen")
        return user

    return checker
