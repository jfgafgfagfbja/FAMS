"""Test cac rang buoc khi mo phien diem danh (POST /sessions): dung ngay hom nay,
dung thu cua lich hoc, trong khung [start - EARLY_OPEN_MINUTES, end], khong trung
phien; va trang thai present/late cua check-in quanh gio bat dau tiet."""
from datetime import date, datetime, time, timedelta

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.db import models
from app.services import face_service
from tests.conftest import auth_headers, login

# "Bay gio" co dinh cho cac test trong file nay: 08:00 giua ngay de moi khung gio
# can dung deu nam tron trong 1 ngay (khong dinh bien nua dem nhu khi dung gio that).
FROZEN_NOW = datetime(2026, 7, 15, 8, 0, 0)


class _FrozenDatetime(datetime):
    """datetime voi now() co dinh - thay the datetime trong module app.api.sessions."""

    @classmethod
    def now(cls, tz=None):
        return FROZEN_NOW


@pytest.fixture()
def frozen_now(monkeypatch):
    """Dong bang datetime.now() trong open_session/recognize + co dinh 2 nguong phut
    (de cac moc gio dung trong test khong phu thuoc config that)."""
    monkeypatch.setattr("app.api.sessions.datetime", _FrozenDatetime)
    monkeypatch.setattr(settings, "EARLY_OPEN_MINUTES", 15)
    monkeypatch.setattr(settings, "LATE_AFTER_MINUTES", 15)
    return FROZEN_NOW


def _make_schedule(db_session, seed, *, start, end, weekday=None):
    """Tao them 1 lich hoc cho class1 (gv1 day) voi gio tuy y; mac dinh dung thu
    cua FROZEN_NOW de qua duoc kiem tra weekday."""
    sched = models.Schedule(
        class_id=seed["class1_id"],
        weekday=FROZEN_NOW.weekday() if weekday is None else weekday,
        start_time=start, end_time=end, room="P201",
    )
    db_session.add(sched)
    db_session.commit()
    return sched


def _try_open(client, schedule_id, session_date):
    token = login(client, "gv1@test.local", "gv123")
    resp = client.post(
        "/sessions",
        json={"schedule_id": schedule_id, "session_date": str(session_date)},
        headers=auth_headers(token),
    )
    return token, resp


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


# ---------------- Rang buoc ngay ----------------

def test_open_session_rejects_past_date(client, seed, db_session, frozen_now):
    yesterday = frozen_now.date() - timedelta(days=1)
    sched = _make_schedule(db_session, seed, start=time(9, 0), end=time(11, 0),
                           weekday=yesterday.weekday())
    _, resp = _try_open(client, sched.id, yesterday)
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Chi duoc mo phien diem danh cho ngay hom nay"


def test_open_session_rejects_future_date(client, seed, db_session, frozen_now):
    tomorrow = frozen_now.date() + timedelta(days=1)
    sched = _make_schedule(db_session, seed, start=time(9, 0), end=time(11, 0),
                           weekday=tomorrow.weekday())
    _, resp = _try_open(client, sched.id, tomorrow)
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Chi duoc mo phien diem danh cho ngay hom nay"


def test_open_session_rejects_wrong_weekday(client, seed, db_session, frozen_now):
    """Hom nay dung la session_date nhung lich hoc lai nam o thu khac."""
    sched = _make_schedule(db_session, seed, start=time(9, 0), end=time(11, 0),
                           weekday=(frozen_now.weekday() + 1) % 7)
    _, resp = _try_open(client, sched.id, frozen_now.date())
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Ngay diem danh khong dung thu cua lich hoc nay"


# ---------------- Rang buoc khung gio ----------------

def test_open_session_rejects_before_early_window(client, seed, db_session, frozen_now):
    """Tiet 09:00 - som nhat duoc mo tu 08:45, luc 08:00 phai bi tu choi kem gio cu the."""
    sched = _make_schedule(db_session, seed, start=time(9, 0), end=time(11, 0))
    _, resp = _try_open(client, sched.id, frozen_now.date())
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Chua den gio - chi mo duoc phien tu 08:45"


def test_open_session_rejects_after_end_time(client, seed, db_session, frozen_now):
    sched = _make_schedule(db_session, seed, start=time(6, 0), end=time(7, 30))
    _, resp = _try_open(client, sched.id, frozen_now.date())
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Tiet hoc da ket thuc, khong the mo phien diem danh"


def test_open_session_ok_within_early_window(client, seed, db_session, frozen_now):
    """Tiet 08:10, khung mo som 15 phut -> 07:55; luc 08:00 mo duoc binh thuong."""
    sched = _make_schedule(db_session, seed, start=time(8, 10), end=time(10, 0))
    _, resp = _try_open(client, sched.id, frozen_now.date())
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "open"


def test_open_session_ok_during_class(client, seed, db_session, frozen_now):
    """Dang giua tiet (08:00 trong 07:30-09:30) van mo duoc (GV mo muon)."""
    sched = _make_schedule(db_session, seed, start=time(7, 30), end=time(9, 30))
    _, resp = _try_open(client, sched.id, frozen_now.date())
    assert resp.status_code == 200, resp.text


# ---------------- Rang buoc trung phien ----------------

def test_open_session_rejects_duplicate_same_schedule_and_date(client, seed, db_session, frozen_now):
    sched = _make_schedule(db_session, seed, start=time(8, 10), end=time(10, 0))
    _, first = _try_open(client, sched.id, frozen_now.date())
    assert first.status_code == 200

    _, second = _try_open(client, sched.id, frozen_now.date())
    assert second.status_code == 400
    assert second.json()["detail"] == "Da co phien diem danh cho lich hoc nay trong ngay hom nay"


def test_unique_constraint_blocks_duplicate_session_at_db_level(db_session, seed):
    """Rang buoc UNIQUE(schedule_id, session_date) phai ton tai o schema - insert
    thang qua ORM bo qua het kiem tra tang app."""
    d = date(2026, 1, 5)
    db_session.add(models.AttendanceSession(
        schedule_id=seed["schedule1_id"], session_date=d, status="closed"))
    db_session.commit()

    db_session.add(models.AttendanceSession(
        schedule_id=seed["schedule1_id"], session_date=d, status="open"))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


# ---------------- present/late quanh gio bat dau (xac nhan logic hien tai) ----------------

def test_checkin_before_start_time_is_present(client, seed, db_session, frozen_now, monkeypatch):
    """SV den som trong khung mo som: check-in luc 08:00 cho tiet 08:10 -> present."""
    monkeypatch.setattr(settings, "CONFIRM_FRAMES", 1)
    sched = _make_schedule(db_session, seed, start=time(8, 10), end=time(10, 0))
    token, resp = _try_open(client, sched.id, frozen_now.date())
    session_id = resp.json()["id"]

    monkeypatch.setattr(face_service, "recognize_frame", _fake_recognize(seed["sv1_id"]))
    frame_resp = _send_frame(client, session_id, token)
    assert frame_resp.json()[0]["status"] == "recognized"

    records = client.get(f"/sessions/{session_id}/records", headers=auth_headers(token)).json()
    assert len(records) == 1
    assert records[0]["status"] == "present"


def test_checkin_after_late_threshold_is_late(client, seed, db_session, frozen_now, monkeypatch):
    """Tiet 07:30, nguong muon 07:45; check-in luc 08:00 -> late."""
    monkeypatch.setattr(settings, "CONFIRM_FRAMES", 1)
    sched = _make_schedule(db_session, seed, start=time(7, 30), end=time(9, 30))
    token, resp = _try_open(client, sched.id, frozen_now.date())
    session_id = resp.json()["id"]

    monkeypatch.setattr(face_service, "recognize_frame", _fake_recognize(seed["sv1_id"]))
    frame_resp = _send_frame(client, session_id, token)
    assert frame_resp.json()[0]["status"] == "recognized"

    records = client.get(f"/sessions/{session_id}/records", headers=auth_headers(token)).json()
    assert records[0]["status"] == "late"


# ---------------- open_from tra ve cho FE ----------------

def test_today_schedules_include_open_from(client, seed):
    """/lecturers/me/today-schedules tra open_from = start_time - EARLY_OPEN_MINUTES
    (dung gio that cua seed nen chi so sanh hieu 2 moc gio, modulo 24h)."""
    token = login(client, "gv1@test.local", "gv123")
    resp = client.get("/lecturers/me/today-schedules", headers=auth_headers(token))
    assert resp.status_code == 200
    entry = next(e for e in resp.json() if e["schedule_id"] == seed["schedule1_id"])

    start = datetime.strptime(entry["start_time"], "%H:%M:%S")
    open_from = datetime.strptime(entry["open_from"], "%H:%M:%S")
    diff_minutes = ((start - open_from).total_seconds() / 60) % (24 * 60)
    assert diff_minutes == settings.EARLY_OPEN_MINUTES
