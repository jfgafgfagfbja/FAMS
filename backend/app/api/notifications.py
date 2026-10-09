"""Hop thu thong bao cua nguoi dang dang nhap (hien dung cho phu huynh - xem
services/parent_notify.py). Moi nguoi chi thay va chi danh dau duoc thong bao cua minh."""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app import schemas
from app.core.security import get_current_user
from app.db import models
from app.db.database import get_db

router = APIRouter(prefix="/notifications", tags=["notifications"])


def _mine(db: Session, user: models.User):
    return db.query(models.Notification).filter(models.Notification.user_id == user.id)


@router.get("", response_model=list[schemas.NotificationOut])
def list_notifications(
    unread_only: bool = False,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    query = _mine(db, user)
    if unread_only:
        query = query.filter(models.Notification.read_at.is_(None))
    return query.order_by(models.Notification.id.desc()).limit(limit).all()


@router.get("/unread-count", response_model=schemas.UnreadCountOut)
def unread_count(
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    return {"count": _mine(db, user).filter(models.Notification.read_at.is_(None)).count()}


@router.post("/read-all")
def mark_all_read(
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    updated = (_mine(db, user).filter(models.Notification.read_at.is_(None))
               .update({models.Notification.read_at: datetime.now()}, synchronize_session=False))
    db.commit()
    return {"updated": updated}


@router.post("/{notification_id}/read", response_model=schemas.NotificationOut)
def mark_read(
    notification_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    # Loc theo user_id ngay trong truy van: thong bao cua nguoi khac tra 404 nhu khong ton
    # tai, khong de lo la co ton tai hay khong.
    item = _mine(db, user).filter(models.Notification.id == notification_id).first()
    if not item:
        raise HTTPException(404, "Thong bao khong ton tai")
    if item.read_at is None:
        item.read_at = datetime.now()
        db.commit()
        db.refresh(item)
    return item
