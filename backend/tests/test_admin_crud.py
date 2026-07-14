"""Test phan trang/tim kiem (GET /students, /classes, /lecturers, /schedules),
FK-check khi xoa (class/lecturer/schedule dang duoc dung), va CRUD giang vien/lich hoc."""
from app.db import models
from tests.conftest import auth_headers, login


def _admin(client):
    return login(client, "admin@test.local", "admin123")


# ---------------- Phan trang + tim kiem ----------------

def test_list_students_search_by_code(client, seed):
    token = _admin(client)
    resp = client.get("/students", params={"q": "SV0001"}, headers=auth_headers(token))
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["student_code"] == "SV0001"


def test_list_students_pagination_header_and_limit(client, seed):
    token = _admin(client)
    resp = client.get("/students", params={"limit": 1, "offset": 0}, headers=auth_headers(token))
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert int(resp.headers["x-total-count"]) == 2  # sv1 + sv2 trong fixture seed


def test_list_students_without_limit_returns_all(client, seed):
    token = _admin(client)
    resp = client.get("/students", headers=auth_headers(token))
    assert len(resp.json()) == 2


def test_list_classes_search_by_code(client, seed):
    token = _admin(client)
    resp = client.get("/classes", params={"q": "C1"}, headers=auth_headers(token))
    body = resp.json()
    assert len(body) == 1
    assert body[0]["class_code"] == "C1"
    assert int(resp.headers["x-total-count"]) == 1


def test_list_lecturers_search_and_pagination(client, seed):
    token = _admin(client)
    resp = client.get("/lecturers", params={"q": "GV Mot"}, headers=auth_headers(token))
    body = resp.json()
    assert len(body) == 1
    assert body[0]["lecturer_code"] == "GV01"


def test_list_all_schedules_admin_only(client, seed):
    admin_token = _admin(client)
    resp = client.get("/schedules", headers=auth_headers(admin_token))
    assert resp.status_code == 200
    assert len(resp.json()) == 2  # schedule1 (C1) + schedule2 (C2)
    assert int(resp.headers["x-total-count"]) == 2

    gv_token = login(client, "gv1@test.local", "gv123")
    resp = client.get("/schedules", headers=auth_headers(gv_token))
    assert resp.status_code == 403


def test_list_all_schedules_search_by_room(client, seed):
    token = _admin(client)
    resp = client.get("/schedules", params={"q": "P102"}, headers=auth_headers(token))
    body = resp.json()
    assert len(body) == 1
    assert body[0]["class_code"] == "C2"


# ---------------- FK-check khi xoa ----------------

def test_delete_class_blocked_when_enrolled(client, seed):
    token = _admin(client)
    resp = client.delete(f"/classes/{seed['class1_id']}", headers=auth_headers(token))
    assert resp.status_code == 409
    assert "ghi danh" in resp.json()["detail"].lower()


def test_delete_class_blocked_when_has_schedule(client, seed):
    token = _admin(client)
    # class2 khong co enrollment (theo fixture seed) nhung co schedule2
    resp = client.delete(f"/classes/{seed['class2_id']}", headers=auth_headers(token))
    assert resp.status_code == 409
    assert "lich hoc" in resp.json()["detail"].lower()


def test_delete_lecturer_blocked_when_has_class(client, seed):
    token = _admin(client)
    resp = client.delete(f"/lecturers/{_lecturer_id_of(client, seed, 'gv1@test.local')}",
                         headers=auth_headers(token))
    assert resp.status_code == 409
    assert "lop hoc phan" in resp.json()["detail"].lower()


def _lecturer_id_of(client, seed, email):
    token = _admin(client)
    lecturers = client.get("/lecturers", headers=auth_headers(token)).json()
    code = "GV01" if email == "gv1@test.local" else "GV02"
    return next(l["id"] for l in lecturers if l["lecturer_code"] == code)


def test_delete_schedule_blocked_when_has_session(client, seed, db_session):
    token = _admin(client)
    from datetime import date
    session = models.AttendanceSession(schedule_id=seed["schedule1_id"], session_date=date.today())
    db_session.add(session)
    db_session.commit()

    resp = client.delete(f"/classes/schedules/{seed['schedule1_id']}", headers=auth_headers(token))
    assert resp.status_code == 409
    assert "phien diem danh" in resp.json()["detail"].lower()


def test_delete_schedule_succeeds_when_unused(client, seed):
    token = _admin(client)
    resp = client.delete(f"/classes/schedules/{seed['schedule2_id']}", headers=auth_headers(token))
    assert resp.status_code == 200


# ---------------- CRUD giang vien / lich hoc ----------------

def test_update_lecturer(client, seed):
    token = _admin(client)
    lid = _lecturer_id_of(client, seed, "gv1@test.local")
    resp = client.patch(f"/lecturers/{lid}", json={"department": "Khoa CNTT moi"},
                        headers=auth_headers(token))
    assert resp.status_code == 200
    assert resp.json()["department"] == "Khoa CNTT moi"


def test_update_lecturer_requires_admin(client, seed):
    gv_token = login(client, "gv1@test.local", "gv123")
    lid = _lecturer_id_of(client, seed, "gv1@test.local")
    resp = client.patch(f"/lecturers/{lid}", json={"department": "x"}, headers=auth_headers(gv_token))
    assert resp.status_code == 403


def test_delete_lecturer_succeeds_when_no_class(client, seed):
    token = _admin(client)
    resp = client.post("/lecturers", json={
        "email": "gv3@fams.edu.vn", "password": "gv123", "full_name": "GV Ba",
        "lecturer_code": "GV03", "department": "CNTT",
    }, headers=auth_headers(token))
    lid = resp.json()["id"]

    resp = client.delete(f"/lecturers/{lid}", headers=auth_headers(token))
    assert resp.status_code == 200


def test_update_schedule(client, seed):
    token = _admin(client)
    resp = client.patch(f"/classes/schedules/{seed['schedule2_id']}",
                        json={"room": "P999", "start_time": "08:00:00"},
                        headers=auth_headers(token))
    assert resp.status_code == 200
    assert resp.json()["room"] == "P999"
    assert resp.json()["start_time"] == "08:00:00"
