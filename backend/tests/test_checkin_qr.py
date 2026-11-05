"""Ma QR diem danh: sinh ma, doi ma theo chu ky, va chan tu diem danh khi khong co ma.

Day la lop xac nhan "co mat dung phong" - GPS chi biet SV o trong khu vuc, con ma QR
thi phai nhin thay man hinh trong phong moi quet duoc.
"""
from datetime import date

import pytest

from app.core.config import settings
from app.db import models
from app.services import checkin_code_service, face_service
from tests.conftest import auth_headers, login


@pytest.fixture()
def matched_face(monkeypatch, db_session, seed):
    """Khuon mat SV1 khop. Ngoai doi chi khop duoc khi SV da dong y va dang ky khuon mat."""
    db_session.get(models.Student, seed["sv1_id"]).consent_given = True
    db_session.commit()
    monkeypatch.setattr(face_service, "recognize_self", lambda db, data, student_id: {
        "status": "matched", "confidence": 0.91, "liveness_score": 0.9, "bbox": [0, 0, 10, 10]})


@pytest.fixture()
def gv_headers(client, seed):
    return auth_headers(login(client, "gv1@test.local", "gv123"))


def _open_session(client, gv_headers, seed, require_qr):
    resp = client.post("/sessions", json={"schedule_id": seed["schedule1_id"],
                                          "session_date": str(date.today()),
                                          "require_qr": require_qr},
                       headers=gv_headers)
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


def _checkin(client, session_id, code=None):
    token = login(client, "sv1@test.local", "sv123")
    data = {}
    if code is not None:
        data["checkin_code"] = code
    return client.post(f"/sessions/{session_id}/self-checkin", data=data,
                       files={"frame": ("f.jpg", b"x", "image/jpeg")}, headers=auth_headers(token))


# ---- Sinh ma ----

def test_lecturer_gets_rotating_code(client, gv_headers, seed):
    session_id = _open_session(client, gv_headers, seed, require_qr=True)
    body = client.get(f"/sessions/{session_id}/checkin-code", headers=gv_headers).json()
    assert body["qr_payload"].startswith(f"FAMS:{session_id}:")
    assert len(body["digits"]) == 6 and body["digits"].isdigit()
    assert body["rotate_seconds"] == settings.CHECKIN_QR_ROTATE_SECONDS
    assert 0 < body["expires_in_seconds"] <= settings.CHECKIN_QR_ROTATE_SECONDS


def test_students_cannot_read_the_code(client, gv_headers, seed):
    """SV lay duoc ma qua API thi khong can co mat trong phong nua."""
    session_id = _open_session(client, gv_headers, seed, require_qr=True)
    token = login(client, "sv1@test.local", "sv123")
    resp = client.get(f"/sessions/{session_id}/checkin-code", headers=auth_headers(token))
    assert resp.status_code == 403


def test_code_differs_between_sessions_and_windows():
    now = checkin_code_service._window()
    assert checkin_code_service._digits(1, now) != checkin_code_service._digits(2, now)
    assert checkin_code_service._digits(1, now) != checkin_code_service._digits(1, now + 1)


def test_expired_window_rejected(monkeypatch):
    """Anh chup man hinh gui qua nhom chat chi dung duoc toi da 2 chu ky."""
    old_window = checkin_code_service._window() - 2
    stale = checkin_code_service._digits(1, old_window)
    assert checkin_code_service.verify(1, stale) is False


def test_previous_window_still_accepted():
    """Quet cham vai giay hoac dong ho lech mot chut van phai diem danh duoc."""
    previous = checkin_code_service._digits(1, checkin_code_service._window() - 1)
    assert checkin_code_service.verify(1, previous) is True


# ---- Tu diem danh ----

def test_checkin_without_code_rejected(client, gv_headers, seed, matched_face):
    session_id = _open_session(client, gv_headers, seed, require_qr=True)
    body = _checkin(client, session_id).json()
    assert body["status"] == "qr_required", body


def test_checkin_with_wrong_code_rejected(client, gv_headers, seed, matched_face):
    session_id = _open_session(client, gv_headers, seed, require_qr=True)
    body = _checkin(client, session_id, code="000000").json()
    assert body["status"] == "qr_invalid", body


def test_code_of_another_session_rejected(client, gv_headers, seed, matched_face):
    session_id = _open_session(client, gv_headers, seed, require_qr=True)
    other = checkin_code_service.current_code(session_id + 999).qr_payload
    assert _checkin(client, session_id, code=other).json()["status"] == "qr_invalid"


def test_checkin_with_qr_payload_succeeds(client, gv_headers, seed, matched_face):
    session_id = _open_session(client, gv_headers, seed, require_qr=True)
    code = client.get(f"/sessions/{session_id}/checkin-code", headers=gv_headers).json()
    body = _checkin(client, session_id, code=code["qr_payload"]).json()
    assert body["status"] == "recognized", body


def test_checkin_with_typed_digits_succeeds(client, gv_headers, seed, matched_face):
    """SV ngoi cuoi phong khong quet duoc QR thi go 6 chu so hien kem."""
    session_id = _open_session(client, gv_headers, seed, require_qr=True)
    code = client.get(f"/sessions/{session_id}/checkin-code", headers=gv_headers).json()
    body = _checkin(client, session_id, code=code["digits"]).json()
    assert body["status"] == "recognized", body


def test_session_without_qr_requirement_unaffected(client, gv_headers, seed, matched_face):
    session_id = _open_session(client, gv_headers, seed, require_qr=False)
    assert client.get(f"/sessions/{session_id}", headers=gv_headers).json()["require_qr"] is False
    assert _checkin(client, session_id).json()["status"] == "recognized"


def test_lecturer_can_turn_qr_on_during_session(client, gv_headers, seed, matched_face):
    """Bat giua buoi: truoc khi bat thi diem danh khong can ma, bat roi thi can."""
    session_id = _open_session(client, gv_headers, seed, require_qr=False)
    resp = client.patch(f"/sessions/{session_id}", json={"require_qr": True}, headers=gv_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["require_qr"] is True
    assert _checkin(client, session_id).json()["status"] == "qr_required"


def test_students_cannot_turn_qr_off(client, gv_headers, seed):
    session_id = _open_session(client, gv_headers, seed, require_qr=True)
    token = login(client, "sv1@test.local", "sv123")
    resp = client.patch(f"/sessions/{session_id}", json={"require_qr": False},
                        headers=auth_headers(token))
    assert resp.status_code == 403


def test_student_sees_whether_qr_is_required(client, gv_headers, seed):
    session_id = _open_session(client, gv_headers, seed, require_qr=True)
    token = login(client, "sv1@test.local", "sv123")
    body = client.get(f"/sessions/{session_id}/checkin-info", headers=auth_headers(token)).json()
    assert body["require_qr"] is True
    assert body["room"]


def test_student_not_enrolled_cannot_read_checkin_info(client, gv_headers, seed):
    session_id = _open_session(client, gv_headers, seed, require_qr=True)
    token = login(client, "sv2@test.local", "sv123")  # khong ghi danh lop nay
    resp = client.get(f"/sessions/{session_id}/checkin-info", headers=auth_headers(token))
    assert resp.status_code == 403
