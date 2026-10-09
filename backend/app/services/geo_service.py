"""Doi chieu vi tri GPS khi SV tu diem danh voi dia diem cua lich hoc."""
import math
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import models

EARTH_RADIUS_M = 6_371_000


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Khoang cach mat dat (met) giua 2 toa do."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


def default_location(db: Session) -> models.Location | None:
    return db.query(models.Location).filter_by(is_default=True).first()


@dataclass
class Geofence:
    """Vong doi chieu thuc te cho mot lich hoc: tam, ban kinh va ten de hien thi."""
    name: str
    latitude: float
    longitude: float
    radius_m: float

    @classmethod
    def from_location(cls, location: models.Location) -> "Geofence":
        return cls(location.name, location.latitude, location.longitude, location.radius_m)

    @classmethod
    def from_room(cls, room: models.Room) -> "Geofence | None":
        """Toa do rieng cua phong neu co; ban kinh khong duoc thap hon muc san vi sai so GPS."""
        if room.latitude is None or room.longitude is None:
            return None
        radius = max(room.radius_m or 0.0, settings.ROOM_MIN_RADIUS_M)
        return cls(room.name, room.latitude, room.longitude, radius)


def resolve_geofence(db: Session, schedule: models.Schedule,
                     fallback: Geofence | None = None) -> Geofence | None:
    """Vong ap dung cho lich hoc, theo thu tu uu tien tu hep den rong:
    toa do rieng cua phong -> khu vuc chua phong -> dia diem gan truc tiep vao lich
    (du lieu cu) -> dia diem mac dinh cua truong.

    `fallback` cho phep ben goi tu truyen vong mac dinh da doc san - dung khi xu ly
    nhieu lich mot luc de khoi truy van lai dia diem mac dinh cho tung lich.
    """
    room = schedule.classroom
    if room is not None:
        fence = Geofence.from_room(room)
        if fence is not None:
            return fence
        if room.location is not None:
            return Geofence.from_location(room.location)
    if schedule.location is not None:
        return Geofence.from_location(schedule.location)
    if fallback is not None:
        return fallback
    location = default_location(db)
    return Geofence.from_location(location) if location is not None else None


@dataclass
class LocationCheck:
    ok: bool
    status: str | None = None  # location_required | location_mocked | location_inaccurate | out_of_range
    message: str = ""
    distance_m: float | None = None
    allowed_radius_m: float | None = None


def check_checkin_location(
    fence: Geofence | None,
    latitude: float | None,
    longitude: float | None,
    accuracy: float | None,
    is_mocked: bool,
) -> LocationCheck:
    """Chi chan khi da cau hinh dia diem va bat SELF_CHECKIN_REQUIRE_LOCATION. Chap nhan sai so
    GPS: hop le khi (khoang cach - sai so) <= ban kinh, voi sai so toi da MAX_ACCURACY."""
    has_position = latitude is not None and longitude is not None
    if fence is None or not settings.SELF_CHECKIN_REQUIRE_LOCATION:
        distance = (haversine_m(latitude, longitude, fence.latitude, fence.longitude)
                    if fence is not None and has_position else None)
        return LocationCheck(ok=True, distance_m=distance)

    radius = fence.radius_m
    if not has_position:
        return LocationCheck(
            ok=False, status="location_required", allowed_radius_m=radius,
            message="Can bat dinh vi va cho phep truy cap vi tri de tu diem danh")
    if is_mocked:
        return LocationCheck(
            ok=False, status="location_mocked", allowed_radius_m=radius,
            message="Phat hien vi tri gia lap, vui long tat ung dung gia lap vi tri")
    if accuracy is not None and accuracy > settings.SELF_CHECKIN_MAX_ACCURACY_M:
        return LocationCheck(
            ok=False, status="location_inaccurate", allowed_radius_m=radius,
            message=f"Vi tri chua du chinh xac (sai so khoang {round(accuracy)} m, can duoi "
                    f"{round(settings.SELF_CHECKIN_MAX_ACCURACY_M)} m). Bat dinh vi chinh xac "
                    "roi thu lai")

    distance = haversine_m(latitude, longitude, fence.latitude, fence.longitude)
    if distance - (accuracy or 0) > radius:
        return LocationCheck(
            ok=False, status="out_of_range", distance_m=distance, allowed_radius_m=radius,
            message=f"Ban dang cach {fence.name} khoang {round(distance)} m, chi duoc tu "
                    f"diem danh trong ban kinh {round(radius)} m")
    return LocationCheck(ok=True, distance_m=distance, allowed_radius_m=radius)
