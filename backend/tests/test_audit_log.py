"""Nhat ky he thong: ghi tu dong moi thay doi du lieu quan ly, ghi dang nhap/xuat bao cao,
khong bao gio luu mat khau, va chi admin/Lanh dao Khoa (trong Khoa minh) xem duoc."""
import json
from datetime import date

import numpy as np
import pytest

from app.core.security import hash_password
from app.db import models
from app.services import face_service
from tests.conftest import consent_body, auth_headers, login


def _logs(db, action=None):
    query = db.query(models.AuditLog).order_by(models.AuditLog.id)
    if action:
        query = query.filter(models.AuditLog.action == action)
    return query.all()


@pytest.fixture()
def admin_headers(client, seed):
    return auth_headers(login(client, "admin@test.local", "admin123"))


# ---------------------------------------------------------------- dang nhap

def test_login_success_is_logged(client, db_session, seed):
    login(client, "admin@test.local", "admin123")
    log = _logs(db_session, "auth.login")[-1]
    assert log.actor_email == "admin@test.local" and log.actor_role == "admin"
    assert log.success is True and log.ip


def test_failed_login_logged_without_password(client, db_session, seed):
    client.post("/auth/login", data={"username": "admin@test.local", "password": "doan-sai-123"})
    log = _logs(db_session, "auth.login_failed")[-1]
    assert log.actor_email == "admin@test.local" and log.success is False
    everything = json.dumps([(l.detail, l.target_label) for l in _logs(db_session)])
    assert "doan-sai-123" not in everything


def test_logout_is_logged(client, db_session, seed):
    token = login(client, "sv1@test.local", "sv123")
    client.post("/auth/logout", json={}, headers=auth_headers(token))
    assert _logs(db_session, "auth.logout")[-1].actor_email == "sv1@test.local"


# ---------------------------------------------------------------- thay doi du lieu

def test_create_is_logged_with_actor(client, db_session, admin_headers):
    loc = models.Location(code="CS", name="Co so", latitude=16.0, longitude=108.2, radius_m=100)
    db_session.add(loc)
    db_session.commit()
    resp = client.post("/rooms", json={"code": "E2-101", "name": "Phong 101", "location_id": loc.id},
                       headers=admin_headers)
    assert resp.status_code == 200, resp.text

    log = _logs(db_session, "room.create")[-1]
    assert log.actor_email == "admin@test.local"
    assert log.target_type == "room" and log.target_id == resp.json()["id"]
    assert log.target_label == "E2-101"


def test_update_records_old_and_new_values(client, db_session, seed, admin_headers):
    resp = client.patch(f"/classes/{seed['class1_id']}", json={"subject_name": "Mon Moi"},
                        headers=admin_headers)
    assert resp.status_code == 200, resp.text
    log = _logs(db_session, "class.update")[-1]
    assert json.loads(log.detail)["subject_name"] == ["Mon 1", "Mon Moi"]


def test_password_change_never_stores_the_hash(client, db_session, seed):
    token = login(client, "gv1@test.local", "gv123")
    client.post("/auth/change-password",
                json={"current_password": "gv123", "new_password": "GiangVien#2026"},
                headers=auth_headers(token))
    log = _logs(db_session, "user.password_changed")[-1]
    assert log.actor_email == "gv1@test.local"
    detail = json.loads(log.detail)
    assert detail["password_hash"] == "(đã thay đổi)"
    assert "$2b$" not in log.detail  # khong lot ban bam bcrypt


def test_face_approval_and_consent_have_readable_names(client, db_session, seed, admin_headers):
    emb = models.FaceEmbedding(student_id=seed["sv1_id"], embedding=np.ones(512).tolist(),
                               status="pending")
    db_session.add(emb)
    db_session.commit()
    client.patch(f"/faces/{emb.id}/approve", headers=admin_headers)
    assert _logs(db_session, "face.approved")

    token = login(client, "sv1@test.local", "sv123")
    client.post(f"/students/{seed['sv1_id']}/consent", json=consent_body(),
                headers=auth_headers(token))
    assert _logs(db_session, "consent.given")


def test_normal_checkin_not_logged_but_edits_are(client, db_session, seed, monkeypatch):
    monkeypatch.setattr(face_service, "recognize_self", lambda db, data, student_id: {
        "status": "matched", "confidence": 0.9, "liveness_score": 0.9, "bbox": [0, 0, 1, 1]})
    db_session.get(models.Student, seed["sv1_id"]).consent_given = True
    db_session.commit()
    gv = auth_headers(login(client, "gv1@test.local", "gv123"))
    session_id = client.post("/sessions", json={"schedule_id": seed["schedule1_id"],
                                                "session_date": str(date.today())},
                             headers=gv).json()["id"]
    assert _logs(db_session, "session.opened")

    sv = auth_headers(login(client, "sv1@test.local", "sv123"))
    client.post(f"/sessions/{session_id}/self-checkin", data={},
                files={"frame": ("f.jpg", b"x", "image/jpeg")}, headers=sv)
    assert _logs(db_session, "attendance.create") == []   # diem danh binh thuong: khong ghi

    record = db_session.query(models.AttendanceRecord).filter_by(session_id=session_id).one()
    client.patch(f"/sessions/{session_id}/records/{record.id}",
                 json={"status": "late", "reason": "den tre"}, headers=gv)
    log = _logs(db_session, "attendance.update")[-1]
    assert log.actor_email == "gv1@test.local"
    assert json.loads(log.detail)["status"][1] == "late"


def test_report_export_is_logged(client, db_session, seed, admin_headers):
    resp = client.get(f"/reports/attendance/export?class_id={seed['class1_id']}&semester=2026.1",
                      headers=admin_headers)
    assert resp.status_code == 200
    log = _logs(db_session, "report.exported")[-1]
    assert log.actor_email == "admin@test.local" and log.target_label == "C1"


# ---------------------------------------------------------------- ai xem duoc

def test_admin_reads_logs_with_filters(client, db_session, seed, admin_headers):
    client.post("/auth/login", data={"username": "sv1@test.local", "password": "sai"})
    resp = client.get("/audit-logs?action=auth.&success=false", headers=admin_headers)
    assert resp.status_code == 200
    rows = resp.json()
    assert rows and all(r["action"].startswith("auth.") and r["success"] is False for r in rows)
    assert int(resp.headers["X-Total-Count"]) == len(rows)


def test_students_and_lecturers_cannot_read_logs(client, seed):
    for email, pw in (("sv1@test.local", "sv123"), ("gv1@test.local", "gv123")):
        headers = auth_headers(login(client, email, pw))
        assert client.get("/audit-logs", headers=headers).status_code == 403


def test_faculty_leader_sees_only_own_faculty(client, db_session, seed, admin_headers):
    cntt = models.Unit(code="K-CNTT", name="Khoa CNTT", type=models.UNIT_FACULTY)
    kt = models.Unit(code="K-KT", name="Khoa Kien truc", type=models.UNIT_FACULTY)
    db_session.add_all([cntt, kt])
    db_session.flush()
    leader = models.User(email="ldk@test.local", password_hash=hash_password("ldk12345"),
                         role=models.ROLE_FACULTY_LEADER, full_name="Truong khoa CNTT")
    db_session.add(leader)
    db_session.flush()
    db_session.add(models.Staff(user_id=leader.id, unit_id=cntt.id))
    db_session.get(models.Class, seed["class1_id"]).faculty_id = cntt.id
    db_session.get(models.Class, seed["class2_id"]).faculty_id = kt.id
    db_session.commit()

    client.patch(f"/classes/{seed['class1_id']}", json={"subject_name": "Mon CNTT"}, headers=admin_headers)
    client.patch(f"/classes/{seed['class2_id']}", json={"subject_name": "Mon KT"}, headers=admin_headers)

    headers = auth_headers(login(client, "ldk@test.local", "ldk12345"))
    rows = client.get("/audit-logs?action=class.update", headers=headers).json()
    # Ca buoc gan lop vao Khoa o tren lan lan admin doi ten mon deu la "sua lop C1" va deu duoc
    # ghi; dieu can kiem la khong lot dong nao cua lop thuoc Khoa Kien truc.
    assert rows and {r["target_label"] for r in rows} == {"C1"}
    assert any("Mon CNTT" in (r["detail"] or "") for r in rows)
