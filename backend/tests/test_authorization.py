from datetime import date

from tests.conftest import auth_headers, login


def test_student_cannot_list_students(client, seed):
    token = login(client, "sv1@test.local", "sv123")
    resp = client.get("/students", headers=auth_headers(token))
    assert resp.status_code == 403


def test_admin_can_list_students(client, seed):
    token = login(client, "admin@test.local", "admin123")
    resp = client.get("/students", headers=auth_headers(token))
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_lecturer_can_open_session_for_own_class(client, seed):
    token = login(client, "gv1@test.local", "gv123")
    resp = client.post(
        "/sessions",
        json={"schedule_id": seed["schedule1_id"], "session_date": str(date.today())},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text


def test_lecturer_cannot_open_session_for_other_lecturers_class(client, seed):
    """gv1 khong duoc mo phien cho lich hoc thuoc lop cua gv2 (schedule2)."""
    token = login(client, "gv1@test.local", "gv123")
    resp = client.post(
        "/sessions",
        json={"schedule_id": seed["schedule2_id"], "session_date": str(date.today())},
        headers=auth_headers(token),
    )
    assert resp.status_code == 403


def test_lecturer_cannot_view_other_lecturers_class_report(client, seed):
    token = login(client, "gv1@test.local", "gv123")
    resp = client.get(f"/reports/attendance/{seed['class2_id']}", headers=auth_headers(token))
    assert resp.status_code == 403


def test_admin_can_view_any_class_report(client, seed):
    token = login(client, "admin@test.local", "admin123")
    resp = client.get(f"/reports/attendance/{seed['class2_id']}", headers=auth_headers(token))
    assert resp.status_code == 200
