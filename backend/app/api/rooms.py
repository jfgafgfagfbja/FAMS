"""Danh muc phong hoc: nguon chon phong khi xep lich, va la mot lop cua viec doi chieu
vi tri khi sinh vien tu diem danh (phong -> khu vuc chua phong)."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app import schemas
from app.core.authz import ACADEMIC_MANAGERS, CLASS_VIEWERS
from app.core.config import settings
from app.core.security import require_roles
from app.db import models
from app.db.database import get_db

router = APIRouter(prefix="/rooms", tags=["rooms"])


def _get_or_404(db: Session, room_id: int) -> models.Room:
    room = db.get(models.Room, room_id)
    if not room:
        raise HTTPException(404, "Phong hoc khong ton tai")
    return room


def _ensure_code_available(db: Session, code: str, exclude_id: int | None = None) -> None:
    query = db.query(models.Room).filter(models.Room.code == code)
    if exclude_id is not None:
        query = query.filter(models.Room.id != exclude_id)
    if query.first():
        raise HTTPException(400, f"Ma phong '{code}' da ton tai")


def _ensure_location(db: Session, location_id: int) -> None:
    if not db.get(models.Location, location_id):
        raise HTTPException(400, "Khu vuc khong ton tai")


def room_out(room: models.Room, schedule_count: int = 0) -> schemas.RoomOut:
    has_own_point = room.latitude is not None and room.longitude is not None
    return schemas.RoomOut(
        id=room.id, code=room.code, name=room.name,
        location_id=room.location_id,
        location_name=room.location.name if room.location else None,
        building=room.building, floor=room.floor, capacity=room.capacity,
        latitude=room.latitude, longitude=room.longitude, radius_m=room.radius_m,
        is_active=room.is_active,
        effective_radius_m=(max(room.radius_m or 0.0, settings.ROOM_MIN_RADIUS_M)
                            if has_own_point else
                            (room.location.radius_m if room.location else None)),
        schedule_count=schedule_count,
    )


@router.get("", response_model=list[schemas.RoomOut])
def list_rooms(
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_roles(*CLASS_VIEWERS)),
    location_id: int | None = None,
    building: str | None = None,
    q: str | None = Query(default=None, description="Tim theo ma hoac ten phong"),
    only_active: bool = True,
):
    query = db.query(models.Room)
    if location_id is not None:
        query = query.filter(models.Room.location_id == location_id)
    if building:
        query = query.filter(models.Room.building == building)
    if only_active:
        query = query.filter(models.Room.is_active.is_(True))
    if q:
        pattern = f"%{q.strip()}%"
        query = query.filter(or_(models.Room.code.ilike(pattern), models.Room.name.ilike(pattern)))
    rooms = query.order_by(models.Room.building, models.Room.floor, models.Room.code).all()

    counts = dict(
        db.query(models.Schedule.room_id, func.count(models.Schedule.id))
        .filter(models.Schedule.room_id.isnot(None))
        .group_by(models.Schedule.room_id).all()
    )
    return [room_out(r, counts.get(r.id, 0)) for r in rooms]


@router.get("/buildings", response_model=list[str])
def list_buildings(
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_roles(*CLASS_VIEWERS)),
):
    """Danh sach toa nha dang co - de loc nhanh o man quan ly va o chon phong."""
    rows = (db.query(models.Room.building).filter(models.Room.building.isnot(None))
            .distinct().order_by(models.Room.building).all())
    return [r[0] for r in rows]


@router.post("", response_model=schemas.RoomOut)
def create_room(
    body: schemas.RoomCreate,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_roles(*ACADEMIC_MANAGERS)),
):
    _ensure_code_available(db, body.code)
    _ensure_location(db, body.location_id)
    room = models.Room(**body.model_dump())
    db.add(room)
    db.commit()
    db.refresh(room)
    return room_out(room)


@router.patch("/{room_id}", response_model=schemas.RoomOut)
def update_room(
    room_id: int,
    body: schemas.RoomUpdate,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_roles(*ACADEMIC_MANAGERS)),
):
    room = _get_or_404(db, room_id)
    data = body.model_dump(exclude_unset=True)
    if "code" in data:
        _ensure_code_available(db, data["code"], exclude_id=room_id)
    if "location_id" in data:
        _ensure_location(db, data["location_id"])
    # Toa do phai con du cap sau khi gop thay doi vao ban ghi hien tai.
    lat = data.get("latitude", room.latitude)
    lng = data.get("longitude", room.longitude)
    if (lat is None) != (lng is None):
        raise HTTPException(400, "Phai co ca vi do va kinh do, hoac bo trong ca hai")
    for field, value in data.items():
        setattr(room, field, value)
    db.commit()
    db.refresh(room)
    return room_out(room)


@router.delete("/{room_id}")
def delete_room(
    room_id: int,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_roles(*ACADEMIC_MANAGERS)),
):
    room = _get_or_404(db, room_id)
    used = db.query(models.Schedule).filter_by(room_id=room_id).count()
    if used:
        raise HTTPException(
            400, f"Phong dang duoc {used} lich hoc su dung. Hay doi phong cho cac lich do, "
                 "hoac danh dau phong ngung su dung thay vi xoa")
    db.delete(room)
    db.commit()
    return {"ok": True}
