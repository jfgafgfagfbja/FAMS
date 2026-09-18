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


def resolve_location(db: Session, schedule: models.Schedule) -> models.Location | None:
    """Dia diem ap dung cho lich hoc: dia diem rieng, neu khong co thi dia diem mac dinh."""
    if schedule.location is not None:
        return schedule.location
    return default_location(db)


@dataclass
class LocationCheck:
    ok: bool
    status: str | None = None  # location_required | location_mocked | location_inaccurate | out_of_range
    message: str = ""
    distance_m: float | None = None
    allowed_radius_m: float | None = None


def check_checkin_location(
    location: models.Location | None,
    latitude: float | None,
    longitude: float | None,
    accuracy: float | None,
    is_mocked: bool,
) -> LocationCheck:
    """Chi chan khi da cau hinh dia diem va bat SELF_CHECKIN_REQUIRE_LOCATION. Chap nhan sai so
    GPS: hop le khi (khoang cach - sai so) <= ban kinh, voi sai so toi da MAX_ACCURACY."""
    has_position = latitude is not None and longitude is not None
    if location is None or not settings.SELF_CHECKIN_REQUIRE_LOCATION:
        distance = (haversine_m(latitude, longitude, location.latitude, location.longitude)
                    if location is not None and has_position else None)
        return LocationCheck(ok=True, distance_m=distance)

    radius = location.radius_m
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

    distance = haversine_m(latitude, longitude, location.latitude, location.longitude)
    if distance - (accuracy or 0) > radius:
        return LocationCheck(
            ok=False, status="out_of_range", distance_m=distance, allowed_radius_m=radius,
            message=f"Ban dang cach {location.name} khoang {round(distance)} m, chi duoc tu "
                    f"diem danh trong ban kinh {round(radius)} m")
    return LocationCheck(ok=True, distance_m=distance, allowed_radius_m=radius)
