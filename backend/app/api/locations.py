from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import schemas
from app.core.authz import ACADEMIC_MANAGERS, CLASS_VIEWERS
from app.core.security import require_roles
from app.db import models
from app.db.database import get_db

router = APIRouter(prefix="/locations", tags=["locations"])


def _get_or_404(db: Session, location_id: int) -> models.Location:
    location = db.get(models.Location, location_id)
    if not location:
        raise HTTPException(404, "Dia diem khong ton tai")
    return location


def _ensure_code_available(db: Session, code: str, exclude_id: int | None = None) -> None:
    existed = db.query(models.Location).filter_by(code=code).first()
    if existed and existed.id != exclude_id:
        raise HTTPException(400, "Ma dia diem da ton tai")


def _clear_other_defaults(db: Session, keep_id: int) -> None:
    (db.query(models.Location)
     .filter(models.Location.id != keep_id, models.Location.is_default.is_(True))
     .update({"is_default": False}))


@router.get("", response_model=list[schemas.LocationOut])
def list_locations(
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_roles(*CLASS_VIEWERS)),
):
    return db.query(models.Location).order_by(models.Location.is_default.desc(), models.Location.name).all()


@router.post("", response_model=schemas.LocationOut)
def create_location(
    body: schemas.LocationCreate,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_roles(*ACADEMIC_MANAGERS)),
):
    _ensure_code_available(db, body.code)
    location = models.Location(**body.model_dump())
    db.add(location)
    db.flush()
    if location.is_default:
        _clear_other_defaults(db, location.id)
    db.commit()
    db.refresh(location)
    return location


@router.patch("/{location_id}", response_model=schemas.LocationOut)
def update_location(
    location_id: int,
    body: schemas.LocationUpdate,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_roles(*ACADEMIC_MANAGERS)),
):
    location = _get_or_404(db, location_id)
    data = body.model_dump(exclude_unset=True)
    if data.get("code"):
        _ensure_code_available(db, data["code"], exclude_id=location_id)
    for field, value in data.items():
        if value is not None:
            setattr(location, field, value)
    if location.is_default:
        _clear_other_defaults(db, location.id)
    db.commit()
    db.refresh(location)
    return location


@router.delete("/{location_id}")
def delete_location(
    location_id: int,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_roles(*ACADEMIC_MANAGERS)),
):
    location = _get_or_404(db, location_id)
    if db.query(models.Schedule).filter_by(location_id=location_id).first():
        raise HTTPException(409, "Dia diem dang duoc gan cho lich hoc, hay doi lich hoc sang dia diem khac truoc")
    db.delete(location)
    db.commit()
    return {"ok": True}
