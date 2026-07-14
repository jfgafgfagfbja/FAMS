"""Test GET /students/me/attendance: chuyen can chi tiet cua chinh SV theo hoc ky."""
from datetime import date

from app.core.config import settings
from tests.conftest import auth_headers, login


def _close_one_session_with_manual_check(client, seed):
    gv_token = login(client, "gv1@test.local", "gv123")
    open_resp = client.post(
        "/sessions", json={"schedule_id": seed["schedule1_id"], "session_date": str(date.today())},
        headers=auth_headers(gv_token),
    )
    session_id = open_resp.json()["id"]
    client.post(f"/sessions/{session_id}/manual", json={"student_id": seed["sv1_id"]},
               headers=auth_headers(gv_token))
    client.patch(f"/sessions/{session_id}/close", headers=auth_headers(gv_token))
    return session_id


def test_my_attendance_returns_class_with_session_detail(client, seed):
    _close_one_session_with_manual_check(client, seed)

    sv_token = login(client, "sv1@test.local", "sv123")
    resp = client.get("/students/me/attendance", headers=auth_headers(sv_token))
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) == 1
    row = rows[0]
    assert row["class_code"] == "C1"
    assert row["manual"] == 1
    assert row["total_sessions"] == 1
    assert len(row["sessions"]) == 1
    assert row["sessions"][0]["status"] == "manual"


def test_my_attendance_includes_lecturer_contact(client, seed):
    _close_one_session_with_manual_check(client, seed)
    sv_token = login(client, "sv1@test.local", "sv123")
    row = client.get("/students/me/attendance", headers=auth_headers(sv_token)).json()[0]
    assert row["lecturer_name"] == "GV Mot"
    assert row["lecturer_email"] == "gv1@test.local"


def test_my_attendance_warn_ratio_matches_settings(client, seed):
    _close_one_session_with_manual_check(client, seed)
    sv_token = login(client, "sv1@test.local", "sv123")
    row = client.get("/students/me/attendance", headers=auth_headers(sv_token)).json()[0]
    assert row["warn_ratio"] == settings.ABSENCE_WARN_RATIO


def test_my_attendance_filters_by_wrong_semester_returns_empty(client, seed):
    _close_one_session_with_manual_check(client, seed)
    sv_token = login(client, "sv1@test.local", "sv123")
    resp = client.get("/students/me/attendance", params={"semester": "1999.9"},
                      headers=auth_headers(sv_token))
    assert resp.status_code == 200
    assert resp.json() == []


def test_my_attendance_denied_for_non_student(client, seed):
    gv_token = login(client, "gv1@test.local", "gv123")
    resp = client.get("/students/me/attendance", headers=auth_headers(gv_token))
    assert resp.status_code == 403


def test_my_attendance_empty_when_not_enrolled_anywhere(client, seed):
    sv2_token = login(client, "sv2@test.local", "sv123")
    resp = client.get("/students/me/attendance", headers=auth_headers(sv2_token))
    assert resp.status_code == 200
    assert resp.json() == []
