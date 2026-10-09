"""Danh muc phong hoc: CRUD, quyen, chan xep trung phong, va anh huong len doi chieu GPS."""
from datetime import date, time

import pytest

from app.core.config import settings
from app.db import models
from app.services import face_service
from tests.conftest import auth_headers, login

CAMPUS = (16.0320, 108.2210)
# ~111 m moi 0.001 do vi do.
ROOM_POINT = (16.0330, 108.2210)   # cach tam co so ~111 m
NEAR_ROOM = (16.0332, 108.2210)    # cach phong ~22 m
FAR = (16.0420, 108.2210)          # cach phong ~1 km


@pytest.fixture()
def campus(db_session, seed):
    location = models.Location(code="CS1", name="Co so chinh", latitude=CAMPUS[0],
                               longitude=CAMPUS[1], radius_m=150, is_default=True)
    db_session.add(location)
    db_session.commit()
    return location


@pytest.fixture()
def admin_headers(client, seed):
    return auth_headers(login(client, "admin@test.local", "admin123"))


def _create_room(client, headers, campus, **over):
    body = {"code": "E2-101", "name": "Phong 101 - Nha E2", "location_id": campus.id,
            "building": "E2", "floor": 1, "capacity": 60}
    body.update(over)
    return client.post("/rooms", json=body, headers=headers)


# ---- CRUD + quyen ----

def test_create_and_list_room(client, admin_headers, campus):
    resp = _create_room(client, admin_headers, campus)
    assert resp.status_code == 200, resp.text
    room = resp.json()
    assert room["code"] == "E2-101"
    assert room["location_name"] == "Co so chinh"
    # Phong chua co toa do rieng -> doi chieu theo ban kinh cua khu vuc.
    assert room["effective_radius_m"] == 150

    listed = client.get("/rooms", headers=admin_headers).json()
    assert [r["code"] for r in listed] == ["E2-101"]


def test_duplicate_room_code_rejected(client, admin_headers, campus):
    assert _create_room(client, admin_headers, campus).status_code == 200
    resp = _create_room(client, admin_headers, campus, name="Phong khac")
    assert resp.status_code == 400
    assert "da ton tai" in resp.json()["detail"]


def test_room_radius_has_floor(client, admin_headers, campus):
    """Ban kinh rieng cua phong duoc nang len muc san vi sai so GPS trong nha."""
    resp = _create_room(client, admin_headers, campus, latitude=ROOM_POINT[0],
                        longitude=ROOM_POINT[1], radius_m=15)
    assert resp.status_code == 200, resp.text
    assert resp.json()["effective_radius_m"] == settings.ROOM_MIN_RADIUS_M


def test_latitude_without_longitude_rejected(client, admin_headers, campus):
    resp = _create_room(client, admin_headers, campus, latitude=ROOM_POINT[0])
    assert resp.status_code == 422


def test_students_cannot_manage_rooms(client, seed, campus):
    headers = auth_headers(login(client, "sv1@test.local", "sv123"))
    assert _create_room(client, headers, campus).status_code == 403


def test_buildings_list(client, admin_headers, campus):
    _create_room(client, admin_headers, campus)
    _create_room(client, admin_headers, campus, code="E3-201", name="Phong 201", building="E3")
    assert client.get("/rooms/buildings", headers=admin_headers).json() == ["E2", "E3"]


def test_inactive_room_hidden_by_default(client, admin_headers, campus):
    room_id = _create_room(client, admin_headers, campus).json()["id"]
    client.patch(f"/rooms/{room_id}", json={"is_active": False}, headers=admin_headers)
    assert client.get("/rooms", headers=admin_headers).json() == []
    assert len(client.get("/rooms?only_active=false", headers=admin_headers).json()) == 1


def test_cannot_delete_room_in_use(client, admin_headers, campus, seed):
    room_id = _create_room(client, admin_headers, campus).json()["id"]
    resp = client.patch(f"/classes/schedules/{seed['schedule1_id']}",
                        json={"room_id": room_id}, headers=admin_headers)
    assert resp.status_code == 200, resp.text
    resp = client.delete(f"/rooms/{room_id}", headers=admin_headers)
    assert resp.status_code == 400
    assert "lich hoc su dung" in resp.json()["detail"]


# ---- Xep lich ----

def test_schedule_takes_room_name(client, admin_headers, campus, seed):
    room_id = _create_room(client, admin_headers, campus).json()["id"]
    resp = client.patch(f"/classes/schedules/{seed['schedule1_id']}",
                        json={"room_id": room_id}, headers=admin_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["room_name"] == "Phong 101 - Nha E2"


def test_same_room_overlapping_time_rejected(client, admin_headers, campus, seed):
    room_id = _create_room(client, admin_headers, campus).json()["id"]
    first = client.post("/classes/schedules", json={
        "class_id": seed["class1_id"], "weekday": 2, "room_id": room_id,
        "start_time": "07:00:00", "end_time": "09:00:00"}, headers=admin_headers)
    assert first.status_code == 200, first.text

    clash = client.post("/classes/schedules", json={
        "class_id": seed["class2_id"], "weekday": 2, "room_id": room_id,
        "start_time": "08:00:00", "end_time": "10:00:00"}, headers=admin_headers)
    assert clash.status_code == 400
    assert "da co lop" in clash.json()["detail"]


def test_back_to_back_slots_allowed(client, admin_headers, campus, seed):
    """Tiet sau bat dau dung luc tiet truoc ket thuc thi khong phai trung phong."""
    room_id = _create_room(client, admin_headers, campus).json()["id"]
    client.post("/classes/schedules", json={
        "class_id": seed["class1_id"], "weekday": 3, "room_id": room_id,
        "start_time": "07:00:00", "end_time": "09:00:00"}, headers=admin_headers)
    resp = client.post("/classes/schedules", json={
        "class_id": seed["class2_id"], "weekday": 3, "room_id": room_id,
        "start_time": "09:00:00", "end_time": "11:00:00"}, headers=admin_headers)
    assert resp.status_code == 200, resp.text


def test_other_weekday_same_room_allowed(client, admin_headers, campus, seed):
    room_id = _create_room(client, admin_headers, campus).json()["id"]
    client.post("/classes/schedules", json={
        "class_id": seed["class1_id"], "weekday": 4, "room_id": room_id,
        "start_time": "07:00:00", "end_time": "09:00:00"}, headers=admin_headers)
    resp = client.post("/classes/schedules", json={
        "class_id": seed["class2_id"], "weekday": 5, "room_id": room_id,
        "start_time": "07:00:00", "end_time": "09:00:00"}, headers=admin_headers)
    assert resp.status_code == 200, resp.text


def test_schedule_needs_a_room(client, admin_headers, seed):
    resp = client.post("/classes/schedules", json={
        "class_id": seed["class1_id"], "weekday": 6,
        "start_time": "07:00:00", "end_time": "09:00:00"}, headers=admin_headers)
    assert resp.status_code == 422


# ---- Doi chieu GPS theo phong ----

@pytest.fixture()
def matched_face(monkeypatch):
    monkeypatch.setattr(face_service, "recognize_self", lambda db, data, student_id: {
        "status": "matched", "confidence": 0.91, "liveness_score": 0.9, "bbox": [0, 0, 10, 10]})


@pytest.fixture()
def session_in_room(client, db_session, admin_headers, campus, seed):
    """Phien diem danh cua lich hoc da gan phong co toa do rieng."""
    room = models.Room(code="E2-101", name="Phong 101 - Nha E2", location_id=campus.id,
                       latitude=ROOM_POINT[0], longitude=ROOM_POINT[1], radius_m=20)
    db_session.add(room)
    db_session.flush()
    schedule = db_session.get(models.Schedule, seed["schedule1_id"])
    schedule.room_id = room.id
    db_session.commit()

    token = login(client, "gv1@test.local", "gv123")
    resp = client.post("/sessions", json={"schedule_id": seed["schedule1_id"],
                                          "session_date": str(date.today())},
                       headers=auth_headers(token))
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


def _checkin(client, session_id, lat, lng, accuracy=5):
    token = login(client, "sv1@test.local", "sv123")
    return client.post(
        f"/sessions/{session_id}/self-checkin",
        data={"latitude": str(lat), "longitude": str(lng), "accuracy": str(accuracy)},
        files={"frame": ("f.jpg", b"x", "image/jpeg")}, headers=auth_headers(token))


def test_checkin_uses_room_coordinates(client, session_in_room, matched_face):
    """Dung canh phong thi dat, du cach tam co so hon 100 m."""
    resp = _checkin(client, session_in_room, *NEAR_ROOM)
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "recognized", resp.json()


def test_checkin_far_from_room_rejected(client, session_in_room, matched_face):
    resp = _checkin(client, session_in_room, *FAR)
    body = resp.json()
    assert body["status"] == "out_of_range", body
    # Ban kinh bao ve nguoi dung la muc san, khong phai 20 m da nhap.
    assert body["allowed_radius_m"] == settings.ROOM_MIN_RADIUS_M


def test_session_detail_shows_room_name(client, session_in_room):
    token = login(client, "gv1@test.local", "gv123")
    detail = client.get(f"/sessions/{session_in_room}", headers=auth_headers(token)).json()
    assert detail["room"] == "Phong 101 - Nha E2"
    assert detail["location_name"] == "Phong 101 - Nha E2"
