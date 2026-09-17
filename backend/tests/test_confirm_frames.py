"""Test multi-frame confirmation: chi ghi attendance record khi du settings.CONFIRM_FRAMES lan."""
from datetime import date

from app.core.config import settings
from app.db import models
from app.services import face_service
from tests.conftest import auth_headers, login


def _open_session(client, seed):
    token = login(client, "gv1@test.local", "gv123")
    resp = client.post(
        "/sessions",
        json={"schedule_id": seed["schedule1_id"], "session_date": str(date.today())},
        headers=auth_headers(token),
    )
    return token, resp.json()["id"]


def _fake_recognize(student_id):
    return lambda db, data, class_id: [
        {"student_id": student_id, "confidence": 0.9, "bbox": [0, 0, 10, 10],
         "is_spoof": False, "liveness_score": 0.95},
    ]


def _send_frame(client, session_id, token):
    return client.post(
        f"/sessions/{session_id}/recognize",
        files={"frame": ("frame.jpg", b"fake", "image/jpeg")},
        headers=auth_headers(token),
    )


def test_below_threshold_frames_do_not_create_record(client, seed, monkeypatch):
    monkeypatch.setattr(settings, "CONFIRM_FRAMES", 3)
    token, session_id = _open_session(client, seed)
    monkeypatch.setattr(face_service, "recognize_frame", _fake_recognize(seed["sv1_id"]))

    for expected_count in (1, 2):
        resp = _send_frame(client, session_id, token)
        body = resp.json()[0]
        assert body["status"] == "confirming"
        assert body["confirm_count"] == expected_count
        assert body["confirm_needed"] == 3

    records = client.get(f"/sessions/{session_id}/records", headers=auth_headers(token))
    assert records.json() == []


def test_reaching_threshold_creates_exactly_one_record(client, seed, monkeypatch):
    monkeypatch.setattr(settings, "CONFIRM_FRAMES", 3)
    token, session_id = _open_session(client, seed)
    monkeypatch.setattr(face_service, "recognize_frame", _fake_recognize(seed["sv1_id"]))

    for _ in range(3):
        resp = _send_frame(client, session_id, token)

    assert resp.json()[0]["status"] == "recognized"

    records = client.get(f"/sessions/{session_id}/records", headers=auth_headers(token)).json()
    assert len(records) == 1
    assert records[0]["student_id"] == seed["sv1_id"]

    # Frame tiep theo sau khi da co record -> already_checked, khong tao record moi
    resp_extra = _send_frame(client, session_id, token)
    assert resp_extra.json()[0]["status"] == "already_checked"
    records_after = client.get(f"/sessions/{session_id}/records", headers=auth_headers(token)).json()
    assert len(records_after) == 1


def test_confirm_counts_are_isolated_per_session(client, seed, db_session, monkeypatch):
    """Dem theo tung session_id rieng, khong lan sang phien khac."""
    monkeypatch.setattr(settings, "CONFIRM_FRAMES", 2)
    token, session_id_1 = _open_session(client, seed)
    monkeypatch.setattr(face_service, "recognize_frame", _fake_recognize(seed["sv1_id"]))
    _send_frame(client, session_id_1, token)  # count=1 cho session_id_1

    # dong phien 1 roi tao phien 2 truc tiep qua ORM (open_session gio chi cho mo
    # phien cua ngay hom nay + chan trung (schedule_id, session_date), nen phien
    # "ngay khac" phai dung du lieu dung san thay vi goi API)
    client.patch(f"/sessions/{session_id_1}/close", headers=auth_headers(token))
    session2 = models.AttendanceSession(
        schedule_id=seed["schedule1_id"], session_date=date(2020, 1, 1), status="open")
    db_session.add(session2)
    db_session.commit()
    session_id_2 = session2.id

    first = _send_frame(client, session_id_2, token)
    assert first.json()[0]["status"] == "confirming"
    assert first.json()[0]["confirm_count"] == 1  # khong ke thua tu phien truoc


def test_confirm_counts_cleared_on_close(client, seed, monkeypatch):
    monkeypatch.setattr(settings, "CONFIRM_FRAMES", 2)
    token, session_id = _open_session(client, seed)
    monkeypatch.setattr(face_service, "recognize_frame", _fake_recognize(seed["sv1_id"]))

    _send_frame(client, session_id, token)
    from app.api.sessions import _confirm_counts
    assert _confirm_counts.get(session_id) == {seed["sv1_id"]: 1}

    client.patch(f"/sessions/{session_id}/close", headers=auth_headers(token))
    assert session_id not in _confirm_counts
