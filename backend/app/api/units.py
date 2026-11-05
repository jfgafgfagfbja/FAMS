from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import schemas
from app.core.security import require_roles
from app.db import models
from app.db.database import get_db
from app.db.models import (FACULTY_ROLES, ROLE_ADMIN, ROLE_AFFAIRS, ROLE_BOARD, ROLE_LECTURER,
                           ROLE_TRAINING)

router = APIRouter(prefix="/units", tags=["units"])

# Danh sach don vi dung cho dropdown chon Khoa o cac form va bo loc thong ke.
UNIT_LIST_VIEWERS = (ROLE_ADMIN, ROLE_TRAINING, ROLE_AFFAIRS, *FACULTY_ROLES, ROLE_BOARD,
                     ROLE_LECTURER)


def _get_unit_or_404(db: Session, unit_id: int) -> models.Unit:
    unit = db.get(models.Unit, unit_id)
    if not unit:
        raise HTTPException(404, "Don vi khong ton tai")
    return unit


def _ensure_code_available(db: Session, code: str, exclude_id: int | None = None) -> None:
    existed = db.query(models.Unit).filter_by(code=code).first()
    if existed and existed.id != exclude_id:
        raise HTTPException(400, "Ma don vi da ton tai")


@router.get("", response_model=list[schemas.UnitOut])
def list_units(
    type: str | None = None,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_roles(*UNIT_LIST_VIEWERS)),
):
    query = db.query(models.Unit)
    if type:
        query = query.filter(models.Unit.type == type)
    return query.order_by(models.Unit.type, models.Unit.name).all()


@router.post("", response_model=schemas.UnitOut)
def create_unit(
    body: schemas.UnitCreate,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_roles(ROLE_ADMIN)),
):
    _ensure_code_available(db, body.code)
    unit = models.Unit(**body.model_dump())
    db.add(unit)
    db.commit()
    db.refresh(unit)
    return unit


@router.patch("/{unit_id}", response_model=schemas.UnitOut)
def update_unit(
    unit_id: int,
    body: schemas.UnitUpdate,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_roles(ROLE_ADMIN)),
):
    """Doi ma/ten don vi. Khong cho doi loai don vi - vai tro can bo suy ra tu loai,
    doi loai se lam lech quyen cua can bo dang thuoc don vi."""
    unit = _get_unit_or_404(db, unit_id)
    data = body.model_dump(exclude_unset=True)
    if data.get("code"):
        _ensure_code_available(db, data["code"], exclude_id=unit_id)
    for field, value in data.items():
        setattr(unit, field, value)
    db.commit()
    db.refresh(unit)
    return unit


@router.delete("/{unit_id}")
def delete_unit(
    unit_id: int,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_roles(ROLE_ADMIN)),
):
    unit = _get_unit_or_404(db, unit_id)
    in_use = (
        db.query(models.Staff).filter_by(unit_id=unit_id).first()
        or db.query(models.Student).filter_by(faculty_id=unit_id).first()
        or db.query(models.Lecturer).filter_by(faculty_id=unit_id).first()
        or db.query(models.Class).filter_by(faculty_id=unit_id).first()
    )
    if in_use:
        raise HTTPException(409, "Don vi dang co can bo/SV/GV/lop hoc phan, khong the xoa")
    db.delete(unit)
    db.commit()
    return {"ok": True}
