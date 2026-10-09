"""Thong bao cho phu huynh moi khi con duoc ghi nhan diem danh: sinh thong bao tu dong,
hop thu trong app, tuy chon cua phu huynh, va tac vu gui email."""
from contextlib import contextmanager
from datetime import date

import pytest

from app.core.config import settings
from app.core.security import hash_password
from app.db import models
from app.services import email_service, face_service, parent_notify
from tests.conftest import auth_headers, login


def _make_parent(db, student_id, email="ph1@test.local", **prefs):
    user = models.User(email=email, password_hash=hash_password("ph123"),
                       role="parent", full_name=f"Phu huynh {email}")
    db.add(user)
    db.flush()
    parent = models.Parent(user_id=user.id, **prefs)
    db.add(parent)
    db.flush()
    db.add(models.ParentStudent(parent_id=parent.id, student_id=student_id))
    db.commit()
    return parent


@pytest.fixture()
def parent(db_session, seed):
    return _make_parent(db_session, seed["sv1_id"])


@pytest.fixture()
def matched_face(monkeypatch):
    monkeypatch.setattr(face_service, "recognize_self", lambda db, data, student_id: {
        "status": "matched", "confidence": 0.91, "liveness_score": 0.9, "bbox": [0, 0, 10, 10]})


@pytest.fixture()
def gv_headers(client, seed):
    return auth_headers(login(client, "gv1@test.local", "gv123"))


@pytest.fixture()
def session_id(client, gv_headers, seed):
    resp = client.post("/sessions", json={"schedule_id": seed["schedule1_id"],
                                          "session_date": str(date.today())}, headers=gv_headers)
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


def _self_checkin(client, session_id):
    token = login(client, "sv1@test.local", "sv123")
    return client.post(f"/sessions/{session_id}/self-checkin", data={},
                       files={"frame": ("f.jpg", b"x", "image/jpeg")}, headers=auth_headers(token))


def _notifications_of(db, parent):
    return (db.query(models.Notification).filter_by(user_id=parent.user_id)
            .order_by(models.Notification.id).all())


# ---------------------------------------------------------------- sinh thong bao

def test_checkin_notifies_parent(client, db_session, parent, session_id, matched_face):
    assert _self_checkin(client, session_id).json()["status"] == "recognized"

    items = _notifications_of(db_session, parent)
    assert len(items) == 1
    n = items[0]
    assert n.kind == parent_notify.KIND_PRESENT
    assert "SV Mot có mặt" in n.title and "C1" in n.title
    assert "SV0001" in n.body and "Mon 1" in n.body
    assert n.link == f"/children/{parent.children[0].student_id}"
    assert n.record_id is not None


def test_every_parent_of_the_student_is_notified(client, db_session, parent, seed,
                                                session_id, matched_face):
    second = _make_parent(db_session, seed["sv1_id"], email="me@test.local")
    _self_checkin(client, session_id)
    assert len(_notifications_of(db_session, parent)) == 1
    assert len(_notifications_of(db_session, second)) == 1


def test_closing_session_notifies_absence(client, db_session, parent, gv_headers, session_id):
    resp = client.patch(f"/sessions/{session_id}/close", headers=gv_headers)
    assert resp.status_code == 200, resp.text

    items = _notifications_of(db_session, parent)
    assert [n.kind for n in items] == [parent_notify.KIND_ABSENT]
    assert "vắng" in items[0].title
    assert "không có ghi nhận điểm danh" in items[0].body


def test_parent_can_mute_present_but_still_gets_absences(client, db_session, seed, gv_headers,
                                                         session_id, matched_face):
    quiet = _make_parent(db_session, seed["sv1_id"], notify_present=False)
    _self_checkin(client, session_id)
    assert _notifications_of(db_session, quiet) == []

    # Phien khac cua lop: vang thi van bao.
    db_session.query(models.AttendanceRecord).delete()
    db_session.commit()
    client.patch(f"/sessions/{session_id}/close", headers=gv_headers)
    assert [n.kind for n in _notifications_of(db_session, quiet)] == [parent_notify.KIND_ABSENT]


def test_status_correction_sends_update(client, db_session, parent, gv_headers, session_id):
    client.patch(f"/sessions/{session_id}/close", headers=gv_headers)
    record = db_session.query(models.AttendanceRecord).filter_by(session_id=session_id).one()

    resp = client.patch(f"/sessions/{session_id}/records/{record.id}",
                        json={"status": "excused", "reason": "Co giay kham benh"}, headers=gv_headers)
    assert resp.status_code == 200, resp.text

    kinds = [n.kind for n in _notifications_of(db_session, parent)]
    assert kinds == [parent_notify.KIND_ABSENT, parent_notify.KIND_EXCUSED]
    assert _notifications_of(db_session, parent)[1].title.startswith("Cập nhật:")


def test_flipping_back_does_not_duplicate(client, db_session, parent, gv_headers, session_id):
    client.patch(f"/sessions/{session_id}/close", headers=gv_headers)
    record = db_session.query(models.AttendanceRecord).filter_by(session_id=session_id).one()
    url = f"/sessions/{session_id}/records/{record.id}"
    for status in ("present", "absent", "present"):
        resp = client.patch(url, json={"status": status, "reason": "sua"}, headers=gv_headers)
        assert resp.status_code == 200, resp.text
    # vang (luc dong phien) + co mat; lan doi qua doi lai sau khong bao trung.
    assert [n.kind for n in _notifications_of(db_session, parent)] == [
        parent_notify.KIND_ABSENT, parent_notify.KIND_PRESENT]


def test_student_without_parent_is_fine(client, db_session, session_id, matched_face):
    assert _self_checkin(client, session_id).json()["status"] == "recognized"
    assert db_session.query(models.Notification).count() == 0


def test_email_skipped_when_smtp_not_configured(client, db_session, parent, session_id,
                                                matched_face, monkeypatch):
    monkeypatch.setattr(settings, "SMTP_HOST", "")
    _self_checkin(client, session_id)
    assert _notifications_of(db_session, parent)[0].email_status == "skipped"


# ---------------------------------------------------------------- hop thu trong app

def test_inbox_read_flow(client, db_session, parent, session_id, gv_headers, matched_face):
    _self_checkin(client, session_id)
    headers = auth_headers(login(client, "ph1@test.local", "ph123"))

    assert client.get("/notifications/unread-count", headers=headers).json() == {"count": 1}
    items = client.get("/notifications", headers=headers).json()
    assert len(items) == 1 and items[0]["read_at"] is None

    resp = client.post(f"/notifications/{items[0]['id']}/read", headers=headers)
    assert resp.status_code == 200 and resp.json()["read_at"] is not None
    assert client.get("/notifications/unread-count", headers=headers).json() == {"count": 0}


def test_read_all(client, db_session, parent, gv_headers, session_id, matched_face):
    _self_checkin(client, session_id)
    record = db_session.query(models.AttendanceRecord).filter_by(session_id=session_id).one()
    client.patch(f"/sessions/{session_id}/records/{record.id}",
                 json={"status": "late", "reason": "den tre"}, headers=gv_headers)
    headers = auth_headers(login(client, "ph1@test.local", "ph123"))
    assert client.get("/notifications/unread-count", headers=headers).json() == {"count": 2}
    assert client.post("/notifications/read-all", headers=headers).json() == {"updated": 2}
    assert client.get("/notifications?unread_only=true", headers=headers).json() == []


def test_cannot_touch_someone_elses_notification(client, db_session, parent, session_id,
                                                 matched_face):
    _self_checkin(client, session_id)
    nid = _notifications_of(db_session, parent)[0].id
    other = auth_headers(login(client, "sv1@test.local", "sv123"))
    assert client.post(f"/notifications/{nid}/read", headers=other).status_code == 404
    assert client.get("/notifications", headers=other).json() == []


# ---------------------------------------------------------------- tuy chon phu huynh

def test_parent_preferences(client, parent):
    headers = auth_headers(login(client, "ph1@test.local", "ph123"))
    body = client.get("/parents/me/preferences", headers=headers).json()
    assert body["notify_email"] is True and body["notify_present"] is True

    resp = client.patch("/parents/me/preferences", json={"notify_present": False}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["notify_present"] is False and resp.json()["notify_email"] is True


def test_only_parents_have_preferences(client, seed):
    headers = auth_headers(login(client, "sv1@test.local", "sv123"))
    assert client.get("/parents/me/preferences", headers=headers).status_code == 403


# ---------------------------------------------------------------- gui email

class _FakeSmtp:
    def __init__(self, fail_for=()):
        self.sent = []
        self.fail_for = set(fail_for)

    def send_message(self, msg):
        if msg["To"] in self.fail_for:
            raise RuntimeError("dia chi nhan bi tu choi")
        self.sent.append(msg)


@pytest.fixture()
def smtp_on(monkeypatch):
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.test.local")
    monkeypatch.setattr(settings, "APP_PUBLIC_URL", "https://fams.example.ts.net")
    fake = _FakeSmtp()

    @contextmanager
    def connection():
        yield fake

    monkeypatch.setattr(email_service, "smtp_connection", connection)
    return fake


def test_pending_email_is_sent(client, db_session, parent, session_id, matched_face, smtp_on):
    _self_checkin(client, session_id)
    assert _notifications_of(db_session, parent)[0].email_status == "pending"

    assert parent_notify.send_pending_emails(db_session) == 1
    n = _notifications_of(db_session, parent)[0]
    assert n.email_status == "sent" and n.emailed_at is not None

    msg = smtp_on.sent[0]
    assert msg["To"] == "ph1@test.local"
    assert msg["Subject"].startswith("[FAMS] SV Mot có mặt")
    text = msg.get_content()
    assert f"https://fams.example.ts.net/#/children/{parent.children[0].student_id}" in text
    # Gui roi thi lan quet sau khong gui lai.
    assert parent_notify.send_pending_emails(db_session) == 0


def test_parent_can_turn_off_email(client, db_session, seed, session_id, matched_face, smtp_on):
    no_mail = _make_parent(db_session, seed["sv1_id"], notify_email=False)
    _self_checkin(client, session_id)
    n = _notifications_of(db_session, no_mail)[0]
    assert n.email_status == "skipped"   # van co trong hop thu, chi khong gui email
    parent_notify.send_pending_emails(db_session)
    assert smtp_on.sent == []


def test_failed_email_retried_then_given_up(client, db_session, parent, session_id,
                                            matched_face, smtp_on, monkeypatch):
    monkeypatch.setattr(settings, "NOTIFY_EMAIL_MAX_ATTEMPTS", 2)
    smtp_on.fail_for.add("ph1@test.local")
    _self_checkin(client, session_id)

    parent_notify.send_pending_emails(db_session)
    n = _notifications_of(db_session, parent)[0]
    assert n.email_status == "pending" and n.email_attempts == 1 and "tu choi" in n.email_error

    parent_notify.send_pending_emails(db_session)
    assert _notifications_of(db_session, parent)[0].email_status == "failed"


def test_smtp_down_does_not_lose_mail(client, db_session, parent, session_id, matched_face,
                                      monkeypatch):
    """May chu email sap: thu van nam trong hang doi de lan sau gui lai."""
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.test.local")

    @contextmanager
    def broken():
        raise ConnectionError("khong ket noi duoc")
        yield  # pragma: no cover

    monkeypatch.setattr(email_service, "smtp_connection", broken)
    _self_checkin(client, session_id)
    assert parent_notify.send_pending_emails(db_session) == 0
    n = _notifications_of(db_session, parent)[0]
    assert n.email_status == "pending" and n.email_attempts == 1
