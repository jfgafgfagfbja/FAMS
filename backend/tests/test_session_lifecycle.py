"""Test toan bo vong doi 1 phien diem danh: open -> manual -> close -> absent tu sinh,
va rang buoc UNIQUE(session_id, student_id) chong ghi trung."""
from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError

from app.db import models
from tests.conftest import auth_headers, login


def _open_session(client, seed, schedule_id=None):
    token = login(client, "gv1@test.local", "gv123")
    resp = client.post(
        "/sessions",
        json={"schedule_id": schedule_id or seed["schedule1_id"], "session_date": str(date.today())},
        headers=auth_headers(token),
    )
    return token, resp.json()["id"]


def test_full_session_lifecycle_manual_then_absent(client, seed, db_session):
    """open -> xac nhan tay 1 SV -> close -> SV do van "manual", SV con lai (chua
    diem danh) tu dong thanh "absent"."""
    # them sv2 vao class1 de co 2 SV cung lop (seed mac dinh chi co sv1 ghi danh class1)
    db_session.add(models.Enrollment(student_id=seed["sv2_id"], class_id=seed["class1_id"]))
    db_session.commit()

    token, session_id = _open_session(client, seed)

    manual_resp = client.post(
        f"/sessions/{session_id}/manual", json={"student_id": seed["sv1_id"]},
        headers=auth_headers(token),
    )
    assert manual_resp.status_code == 200
    assert manual_resp.json()["status"] == "manual"

    close_resp = client.patch(f"/sessions/{session_id}/close", headers=auth_headers(token))
    assert close_resp.status_code == 200
    body = close_resp.json()
    assert body["present"] == 1   # sv1 da co record (manual)
    assert body["absent"] == 1    # sv2 chua diem danh -> vang tu dong

    records = {
        r["student_id"]: r["status"]
        for r in client.get(f"/sessions/{session_id}/records", headers=auth_headers(token)).json()
    }
    assert records[seed["sv1_id"]] == "manual"
    assert records[seed["sv2_id"]] == "absent"


def test_manual_check_twice_rejected_with_400(client, seed):
    """Chan trung o tang app truoc khi cham UNIQUE constraint (tranh 500 kho hieu)."""
    token, session_id = _open_session(client, seed)

    first = client.post(f"/sessions/{session_id}/manual", json={"student_id": seed["sv1_id"]},
                        headers=auth_headers(token))
    assert first.status_code == 200

    second = client.post(f"/sessions/{session_id}/manual", json={"student_id": seed["sv1_id"]},
                         headers=auth_headers(token))
    assert second.status_code == 400


def test_unique_constraint_blocks_duplicate_record_at_db_level(db_session, seed):
    """Kiem tra rang buoc UNIQUE(session_id, student_id) thuc su ton tai o schema,
    bo qua het logic kiem tra trung o tang app (insert thang qua ORM)."""
    session = models.AttendanceSession(
        schedule_id=seed["schedule1_id"], session_date=date.today(), status="open")
    db_session.add(session)
    db_session.flush()

    db_session.add(models.AttendanceRecord(
        session_id=session.id, student_id=seed["sv1_id"], status="manual"))
    db_session.commit()

    db_session.add(models.AttendanceRecord(
        session_id=session.id, student_id=seed["sv1_id"], status="present"))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
