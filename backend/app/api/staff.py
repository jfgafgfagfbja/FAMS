from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app import schemas
from app.api.auth import reset_password_by_manager
from app.api.serializers import (delete_user_auth_rows, ensure_email_available,
                                 ensure_no_audit_history, staff_out)
from app.core.security import hash_password, require_roles
from app.db import models
from app.db.database import get_db
from app.db.models import (ROLE_ADMIN, ROLE_BY_UNIT_TYPE, ROLE_FACULTY, ROLE_FACULTY_LEADER,
                           UNIT_FACULTY)

router = APIRouter(prefix="/staff", tags=["staff"])


def _get_unit(db: Session, unit_id: int) -> models.Unit:
    unit = db.get(models.Unit, unit_id)
    if not unit:
        raise HTTPException(400, "Don vi khong ton tai")
    return unit


def _get_staff_or_404(db: Session, staff_id: int) -> models.Staff:
    staff = db.get(models.Staff, staff_id)
    if not staff:
        raise HTTPException(404, "Can bo khong ton tai")
    return staff


@router.get("", response_model=list[schemas.StaffOut])
def list_staff(
    response: Response,
    q: str | None = None,
    unit_id: int | None = None,
    limit: int | None = None,
    offset: int = 0,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_roles(ROLE_ADMIN)),
):
    query = db.query(models.Staff).join(models.User, models.Staff.user_id == models.User.id)
    if q:
        like = f"%{q}%"
        query = query.filter(or_(models.User.full_name.ilike(like),
                                 models.User.email.ilike(like)))
    if unit_id is not None:
        query = query.filter(models.Staff.unit_id == unit_id)

    response.headers["X-Total-Count"] = str(query.count())
    query = query.order_by(models.User.full_name).offset(offset)
    if limit is not None:
        query = query.limit(limit)
    return [staff_out(s) for s in query.all()]


def _role_for(unit: models.Unit, faculty_leader: bool) -> str:
    """Vai tro cua can bo theo don vi. Don vi Khoa co hai vai tro: Lanh dao Khoa hoac Van
    phong Khoa; cac don vi khac chi co mot."""
    if unit.type == UNIT_FACULTY:
        return ROLE_FACULTY_LEADER if faculty_leader else ROLE_FACULTY
    if faculty_leader:
        raise HTTPException(400, "Chi don vi loai Khoa moi co Lanh dao Khoa")
    return ROLE_BY_UNIT_TYPE[unit.type]


@router.post("", response_model=schemas.StaffOut)
def create_staff(
    body: schemas.StaffCreate,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_roles(ROLE_ADMIN)),
):
    """Tao tai khoan can bo phong ban. Vai tro suy ra tu loai don vi (Khoa -> Van phong
    Khoa, hoac Lanh dao Khoa neu faculty_leader; P.Dao tao, P.CTSV, Ban nganh)."""
    ensure_email_available(db, body.email)
    unit = _get_unit(db, body.unit_id)
    user = models.User(email=body.email, password_hash=hash_password(body.password),
                       role=_role_for(unit, body.faculty_leader), full_name=body.full_name)
    db.add(user)
    db.flush()
    staff = models.Staff(user_id=user.id, unit_id=unit.id, position=body.position)
    db.add(staff)
    db.commit()
    db.refresh(staff)
    return staff_out(staff)


@router.patch("/{staff_id}", response_model=schemas.StaffOut)
def update_staff(
    staff_id: int,
    body: schemas.StaffUpdate,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_roles(ROLE_ADMIN)),
):
    """Sua can bo; chuyen don vi thi vai tro doi theo loai don vi moi (co hieu luc ngay
    vi quyen luon doc tu DB, khong tu role trong token)."""
    staff = _get_staff_or_404(db, staff_id)
    data = body.model_dump(exclude_unset=True)
    if data.get("full_name"):
        staff.user.full_name = data["full_name"]
    if "position" in data and data["position"] is not None:
        staff.position = data["position"]
    if data.get("unit_id") is not None or data.get("faculty_leader") is not None:
        unit = _get_unit(db, data["unit_id"]) if data.get("unit_id") is not None else staff.unit
        leader = (data["faculty_leader"] if data.get("faculty_leader") is not None
                  else staff.user.role == ROLE_FACULTY_LEADER)
        staff.unit_id = unit.id
        staff.user.role = _role_for(unit, leader)
    db.commit()
    db.refresh(staff)
    return staff_out(staff)


@router.post("/{staff_id}/reset-password")
def reset_staff_password(
    staff_id: int,
    body: schemas.ManagerResetPasswordRequest,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_roles(ROLE_ADMIN)),
):
    staff = db.get(models.Staff, staff_id)
    if not staff:
        raise HTTPException(404, "Can bo khong ton tai")
    reset_password_by_manager(db, staff.user, body.new_password)
    return {"ok": True}


@router.delete("/{staff_id}")
def delete_staff(
    staff_id: int,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_roles(ROLE_ADMIN)),
):
    staff = _get_staff_or_404(db, staff_id)
    user = staff.user
    ensure_no_audit_history(db, user.id)
    delete_user_auth_rows(db, user.id)
    db.delete(staff)
    db.delete(user)
    db.commit()
    return {"ok": True}
