from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db import models


def ensure_class_access(user: models.User, class_id: int, db: Session) -> None:
    """Admin duoc thao tac moi lop. Giang vien chi duoc thao tac lop minh day."""
    if user.role == "admin":
        return
    if user.role == "lecturer":
        lecturer = db.query(models.Lecturer).filter_by(user_id=user.id).first()
        clazz = db.get(models.Class, class_id)
        if lecturer and clazz and clazz.lecturer_id == lecturer.id:
            return
    raise HTTPException(status.HTTP_403_FORBIDDEN, "Khong co quyen voi lop hoc phan nay")
