def check_checkin_location(
    fence: Geofence | None,
    latitude: float | None,
    longitude: float | None,
    accuracy: float | None,
    is_mocked: bool,
) -> LocationCheck:
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
