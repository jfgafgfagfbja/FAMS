"""Test canh bao chuyen can (Task A) va xuat Excel (Task B)."""
import io
from datetime import date

from openpyxl import load_workbook

from app.db import models
from tests.conftest import auth_headers, login


def _make_closed_session(db_session, schedule_id, session_date, status_by_student):
    """Tao 1 phien da dong voi record cho tung SV theo status chi dinh - dung de
    dung nhanh du lieu lich su nhieu buoi hoc cho test, khong di qua HTTP."""
    session = models.AttendanceSession(
        schedule_id=schedule_id, session_date=session_date, status="closed")
    db_session.add(session)
    db_session.flush()
    for student_id, status in status_by_student.items():
        db_session.add(models.AttendanceRecord(
            session_id=session.id, student_id=student_id, status=status))
    db_session.commit()
    return session


def _open_session(client, seed):
    token = login(client, "gv1@test.local", "gv123")
    resp = client.post(
        "/sessions",
        json={"schedule_id": seed["schedule1_id"], "session_date": str(date.today())},
        headers=auth_headers(token),
    )
    return token, resp.json()["id"]


# ---------------- Task A: canh bao chuyen can ----------------

def test_attendance_warnings_lists_students_over_threshold(client, seed, db_session):
    for i in range(5):
        status = "absent" if i < 2 else "present"
        _make_closed_session(db_session, seed["schedule1_id"], date(2026, 1, i + 1),
                             {seed["sv1_id"]: status})

    token = login(client, "gv1@test.local", "gv123")
    resp = client.get("/reports/attendance/warnings", params={"class_id": seed["class1_id"]},
                      headers=auth_headers(token))
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["student_id"] == seed["sv1_id"]
    assert body[0]["absent"] == 2
    assert body[0]["total_sessions"] == 5
    assert body[0]["warning"] is True


def test_attendance_warnings_excludes_excused(client, seed, db_session):
    """excused khong tinh la vang - 2/5 excused khong duoc canh bao."""
    for i in range(5):
        status = "excused" if i < 2 else "present"
        _make_closed_session(db_session, seed["schedule1_id"], date(2026, 1, i + 1),
                             {seed["sv1_id"]: status})

    token = login(client, "gv1@test.local", "gv123")
    resp = client.get("/reports/attendance/warnings", params={"class_id": seed["class1_id"]},
                      headers=auth_headers(token))
    assert resp.status_code == 200
    assert resp.json() == []


def test_attendance_warnings_denied_for_other_lecturer(client, seed):
    token = login(client, "gv2@test.local", "gv123")
    resp = client.get("/reports/attendance/warnings", params={"class_id": seed["class1_id"]},
                      headers=auth_headers(token))
    assert resp.status_code == 403


def test_close_session_returns_newly_warned(client, seed, db_session):
    """4 buoi truoc sv1 luon co mat (chua canh bao); dong phien thu 5 ma sv1 khong
    diem danh -> vang -> ti le 1/5 = 20% vua vuot nguong -> xuat hien trong newly_warned."""
    for i in range(4):
        _make_closed_session(db_session, seed["schedule1_id"], date(2026, 1, i + 1),
                             {seed["sv1_id"]: "present"})

    token, session_id = _open_session(client, seed)
    resp = client.patch(f"/sessions/{session_id}/close", headers=auth_headers(token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["absent"] == 1

    newly_warned = body["newly_warned"]
    assert len(newly_warned) == 1
    assert newly_warned[0]["student_id"] == seed["sv1_id"]
    assert newly_warned[0]["total_sessions"] == 5


def test_close_session_no_newly_warned_when_no_one_crosses(client, seed, db_session):
    token, session_id = _open_session(client, seed)
    resp = client.patch(f"/sessions/{session_id}/close", headers=auth_headers(token))
    assert resp.status_code == 200
    # 1 buoi, sv1 vang -> 100% >= 20%, nhung day la lan dau nen van "vua vuot nguong"
    assert len(resp.json()["newly_warned"]) == 1


# ---------------- Task B: xuat Excel ----------------

def test_export_returns_valid_xlsx(client, seed, db_session):
    _make_closed_session(db_session, seed["schedule1_id"], date(2026, 1, 1),
                         {seed["sv1_id"]: "absent"})
    _make_closed_session(db_session, seed["schedule1_id"], date(2026, 1, 2),
                         {seed["sv1_id"]: "present"})

    token = login(client, "gv1@test.local", "gv123")
    resp = client.get(
        "/reports/attendance/export",
        params={"class_id": seed["class1_id"], "semester": "2026.1"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    assert 'diemdanh_C1_2026.1.xlsx' in resp.headers["content-disposition"]

    wb = load_workbook(io.BytesIO(resp.content))
    assert wb.sheetnames == ["Diem danh", "Thong ke lop"]

    ws1 = wb["Diem danh"]
    header = [c.value for c in next(ws1.iter_rows(min_row=1, max_row=1))]
    assert header == ["MSSV", "Ho ten", "01/01/2026", "02/01/2026", "Tong vang", "% vang"]

    sv1_row = [c.value for c in next(ws1.iter_rows(min_row=2, max_row=2))]
    assert sv1_row[0] == "SV0001"
    assert sv1_row[2] == "A"
    assert sv1_row[3] == "P"
    assert sv1_row[4] == 1  # tong vang

    ws2 = wb["Thong ke lop"]
    summary = {row[0].value: row[1].value for row in ws2.iter_rows(min_row=1, max_row=7)}
    assert summary["Ma lop"] == "C1"
    assert summary["Tong so buoi da diem danh"] == 2


def test_export_denied_for_other_lecturer(client, seed):
    token = login(client, "gv2@test.local", "gv123")
    resp = client.get(
        "/reports/attendance/export",
        params={"class_id": seed["class1_id"], "semester": "2026.1"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 403


def test_export_rejects_mismatched_semester(client, seed):
    token = login(client, "gv1@test.local", "gv123")
    resp = client.get(
        "/reports/attendance/export",
        params={"class_id": seed["class1_id"], "semester": "2099.2"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 400
