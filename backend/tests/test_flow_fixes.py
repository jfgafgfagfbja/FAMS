"""Cac loi luong nghiep vu da xac nhan khi kiem tra du an - moi test giu cho loi khong tai phat."""
from datetime import date, datetime, time, timedelta

from app.core.config import settings
from app.db import models
from app.services import face_service
from app.services.session_service import auto_close_expired_sessions
from tests.conftest import consent_body, auth_headers, login


def _open_session(client, seed):
    token = login(client, "gv1@test.local", "gv123")
    resp = client.post("/sessions", json={"schedule_id": seed["schedule1_id"],
                                          "session_date": str(date.today())},
                       headers=auth_headers(token))
    assert resp.status_code == 200, resp.text
    return token, resp.json()["id"]


def _admin(client):
    return auth_headers(login(client, "admin@test.local", "admin123"))


# ---------------- Diem danh ----------------

def test_manual_check_rejects_student_outside_class(client, seed):
    token, session_id = _open_session(client, seed)
    resp = client.post(f"/sessions/{session_id}/manual", json={"student_id": seed["sv2_id"]},
                       headers=auth_headers(token))
    assert resp.status_code == 400


def test_manual_check_rejected_after_close(client, seed):
    token, session_id = _open_session(client, seed)
    client.patch(f"/sessions/{session_id}/close", headers=auth_headers(token))
    resp = client.post(f"/sessions/{session_id}/manual", json={"student_id": seed["sv1_id"]},
                       headers=auth_headers(token))
    assert resp.status_code == 400


def test_close_session_twice_rejected(client, seed):
    token, session_id = _open_session(client, seed)
    assert client.patch(f"/sessions/{session_id}/close", headers=auth_headers(token)).status_code == 200
    assert client.patch(f"/sessions/{session_id}/close", headers=auth_headers(token)).status_code == 400


def test_update_record_requires_reason_and_rejects_manual_status(client, seed):
    token, session_id = _open_session(client, seed)
    client.patch(f"/sessions/{session_id}/close", headers=auth_headers(token))
    record = client.get(f"/sessions/{session_id}/records", headers=auth_headers(token)).json()[0]
    url = f"/sessions/{session_id}/records/{record['id']}"
    assert client.patch(url, json={"status": "present"}, headers=auth_headers(token)).status_code == 422
    assert client.patch(url, json={"status": "manual", "reason": "x"},
                        headers=auth_headers(token)).status_code == 400
    assert client.patch(url, json={"status": "excused", "reason": "Co don"},
                        headers=auth_headers(token)).status_code == 200


def test_checkin_rejected_after_deadline(client, db_session, seed, monkeypatch):
    """Phien van 'open' nhung da qua gio ket thuc tiet + SESSION_GRACE_MINUTES."""
    token, session_id = _open_session(client, seed)
    session = db_session.get(models.AttendanceSession, session_id)
    session.session_date = date.today() - timedelta(days=7)
    db_session.commit()

    monkeypatch.setattr(face_service, "recognize_frame", lambda db, data, class_id: [])
    resp = client.post(f"/sessions/{session_id}/recognize",
                       files={"frame": ("f.jpg", b"x", "image/jpeg")}, headers=auth_headers(token))
    assert resp.status_code == 400

    sv_token = login(client, "sv1@test.local", "sv123")
    resp = client.post(f"/sessions/{session_id}/self-checkin",
                       files={"frame": ("f.jpg", b"x", "image/jpeg")}, headers=auth_headers(sv_token))
    assert resp.status_code == 400


def test_auto_close_expired_sessions_marks_absent(db_session, seed):
    schedule = db_session.get(models.Schedule, seed["schedule1_id"])
    session = models.AttendanceSession(schedule_id=schedule.id,
                                       session_date=date.today() - timedelta(days=7))
    db_session.add(session)
    db_session.commit()

    assert auto_close_expired_sessions(db_session) == 1
    db_session.refresh(session)
    assert session.status == "closed"
    statuses = [r.status for r in session.records]
    assert statuses == ["absent"]  # sv1 ghi danh class1, chua diem danh


def test_auto_close_keeps_sessions_within_deadline(db_session, seed):
    session = models.AttendanceSession(schedule_id=seed["schedule1_id"], session_date=date.today())
    db_session.add(session)
    db_session.commit()
    now = datetime.combine(date.today(), db_session.get(models.Schedule, seed["schedule1_id"]).end_time)
    assert auto_close_expired_sessions(db_session, now=now) == 0


def test_session_detail_datetimes_include_offset(client, seed):
    token, session_id = _open_session(client, seed)
    body = client.get(f"/sessions/{session_id}", headers=auth_headers(token)).json()
    assert body["opened_at"].endswith("+07:00")
    assert body["checkin_deadline"].endswith("+07:00")


def test_today_schedules_include_opened_session(client, seed):
    token, session_id = _open_session(client, seed)
    entries = client.get("/lecturers/me/today-schedules", headers=auth_headers(token)).json()
    entry = next(e for e in entries if e["schedule_id"] == seed["schedule1_id"])
    assert entry["session_id"] == session_id
    assert entry["session_status"] == "open"


# ---------------- Phan quyen giang vien ----------------

def test_lecturer_cannot_read_other_class_students(client, seed):
    token = login(client, "gv2@test.local", "gv123")
    resp = client.get(f"/classes/{seed['class1_id']}/students", headers=auth_headers(token))
    assert resp.status_code == 403


def test_lecturer_session_list_scoped_to_own_classes(client, seed):
    _, session_id = _open_session(client, seed)
    token = login(client, "gv2@test.local", "gv123")
    sessions = client.get("/sessions", headers=auth_headers(token)).json()
    assert all(s["id"] != session_id for s in sessions)


def test_lecturer_cannot_enroll_face_for_student_outside_classes(client, seed):
    admin = _admin(client)
    client.post(f"/students/{seed['sv2_id']}/consent", json=consent_body("paper"), headers=admin)
    token = login(client, "gv1@test.local", "gv123")
    resp = client.post(f"/faces/enroll/{seed['sv2_id']}", headers=auth_headers(token),
                       files={"images": ("f.jpg", b"x", "image/jpeg")})
    assert resp.status_code == 403


def test_student_cannot_read_class_detail(client, seed):
    token = login(client, "sv1@test.local", "sv123")
    assert client.get(f"/classes/{seed['class1_id']}", headers=auth_headers(token)).status_code == 403
    # ... nhung van xem duoc lich hoc lop minh ghi danh
    assert client.get(f"/classes/{seed['class1_id']}/schedules",
                      headers=auth_headers(token)).status_code == 200
    assert client.get(f"/classes/{seed['class2_id']}/schedules",
                      headers=auth_headers(token)).status_code == 403


# ---------------- Loi 500 -> ma loi ro rang ----------------

def test_delete_parent_with_linked_child(client, seed):
    h = _admin(client)
    parent = client.post("/parents", json={"email": "ph@fams.edu.vn", "password": "12345678",
                                           "full_name": "PH"}, headers=h).json()
    client.post(f"/parents/{parent['id']}/children", json={"student_code": "SV0001"}, headers=h)
    assert client.delete(f"/parents/{parent['id']}", headers=h).status_code == 200
    assert client.get(f"/students/{seed['sv1_id']}", headers=h).status_code == 200


def test_delete_student_linked_to_parent(client, seed):
    h = _admin(client)
    parent = client.post("/parents", json={"email": "ph2@fams.edu.vn", "password": "12345678",
                                           "full_name": "PH2"}, headers=h).json()
    client.post(f"/parents/{parent['id']}/children", json={"student_code": "SV0002"}, headers=h)
    assert client.delete(f"/students/{seed['sv2_id']}", headers=h).status_code == 200
    assert client.get(f"/parents/{parent['id']}/children", headers=h).json() == []


def test_delete_student_with_attendance_history_returns_409(client, db_session, seed):
    session = models.AttendanceSession(schedule_id=seed["schedule2_id"],
                                       session_date=date(2026, 1, 6), status="closed")
    db_session.add(session)
    db_session.flush()
    db_session.add(models.AttendanceRecord(session_id=session.id, student_id=seed["sv2_id"],
                                           status="absent"))
    db_session.commit()
    assert client.delete(f"/students/{seed['sv2_id']}", headers=_admin(client)).status_code == 409


def test_duplicate_codes_return_400(client, seed):
    h = _admin(client)
    resp = client.post("/students", json={"email": "new@fams.edu.vn", "password": "x",
                                          "full_name": "N", "student_code": "SV0001"}, headers=h)
    assert resp.status_code == 400
    resp = client.post("/lecturers", json={"email": "gvx@fams.edu.vn", "password": "x",
                                           "full_name": "G", "lecturer_code": "GV01"}, headers=h)
    assert resp.status_code == 400
    lecturer_id = client.get("/lecturers", headers=h).json()[0]["id"]
    resp = client.post("/classes", json={"class_code": "C1", "subject_name": "Trung",
                                         "lecturer_id": lecturer_id, "semester": "2026.1"}, headers=h)
    assert resp.status_code == 400


def test_enroll_nonexistent_student_or_class_returns_404(client, seed):
    h = _admin(client)
    assert client.post(f"/classes/{seed['class1_id']}/enroll/999999", headers=h).status_code == 404
    assert client.post(f"/classes/999999/enroll/{seed['sv1_id']}", headers=h).status_code == 404


def test_schedule_validation(client, seed):
    h = _admin(client)
    resp = client.post("/classes/schedules", json={
        "class_id": seed["class1_id"], "weekday": 9, "start_time": "08:00:00",
        "end_time": "10:00:00", "room": "X"}, headers=h)
    assert resp.status_code == 422
    resp = client.post("/classes/schedules", json={
        "class_id": seed["class1_id"], "weekday": 1, "start_time": "10:00:00",
        "end_time": "08:00:00", "room": "X"}, headers=h)
    assert resp.status_code == 422
    resp = client.patch(f"/classes/schedules/{seed['schedule1_id']}",
                        json={"end_time": "00:00:01"}, headers=h)
    assert resp.status_code == 400


def test_login_limit_is_per_account(client, seed):
    """5 lan sai cua 1 tai khoan khong khoa tai khoan khac cung IP."""
    for _ in range(5):
        client.post("/auth/login", data={"username": "sv1@test.local", "password": "sai"})
    assert client.post("/auth/login", data={"username": "sv1@test.local",
                                            "password": "sv123"}).status_code == 429
    assert client.post("/auth/login", data={"username": "sv2@test.local",
                                            "password": "sv123"}).status_code == 200
