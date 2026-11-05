"""Xem nhat ky he thong. Admin xem toan truong; Lanh dao Khoa chi xem cac thao tac lien quan
den Khoa minh (theo cot faculty_id ghi luc phat sinh - xem services/audit.py)."""
from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app import schemas
from app.core.authz import staff_unit_id
from app.core.security import require_roles
from app.db import models
from app.db.database import get_db
from app.db.models import ROLE_ADMIN, ROLE_FACULTY_LEADER

router = APIRouter(prefix="/audit-logs", tags=["audit"])

AUDIT_VIEWERS = (ROLE_ADMIN, ROLE_FACULTY_LEADER)


@router.get("", response_model=list[schemas.AuditLogOut])
def list_audit_logs(
    response: Response,
    q: str | None = Query(default=None, description="Tim theo email nguoi thao tac, doi tuong, hanh dong"),
    action: str | None = Query(default=None, description="Loc theo nhom, vd 'auth.' hoac 'student.'"),
    success: bool | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles(*AUDIT_VIEWERS)),
):
    query = db.query(models.AuditLog)
    if user.role == ROLE_FACULTY_LEADER:
        unit_id = staff_unit_id(user, db)
        query = query.filter(models.AuditLog.faculty_id == (unit_id if unit_id is not None else -1))
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(or_(models.AuditLog.actor_email.ilike(like),
                                 models.AuditLog.target_label.ilike(like),
                                 models.AuditLog.action.ilike(like)))
    if action:
        query = query.filter(models.AuditLog.action.startswith(action))
    if success is not None:
        query = query.filter(models.AuditLog.success.is_(success))
    if date_from:
        query = query.filter(models.AuditLog.created_at >= datetime.combine(date_from, time.min))
    if date_to:
        query = query.filter(models.AuditLog.created_at < datetime.combine(date_to + timedelta(days=1), time.min))

    response.headers["X-Total-Count"] = str(query.count())
    return (query.order_by(models.AuditLog.id.desc())
            .offset(offset).limit(limit).all())
