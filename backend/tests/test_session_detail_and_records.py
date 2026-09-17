from datetime import date

from tests.conftest import auth_headers, login


def _open_session(client, seed, lecturer_email="gv1@test.local", schedule_id=None):
    token = login(client, lecturer_email, "gv123")
    resp = client.post(
        "/sessions",
        json={"schedule_id": schedule_id or seed["schedule1_id"], "session_date": str(date.today())},
        headers=auth_headers(token),
    )
    return token, resp.json()["id"]


def test_get_session_detail_returns_class_info(client, seed):
    token, session_id = _open_session(client, seed)
    resp = client.get(f"/sessions/{session_id}", headers=auth_headers(token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["class_id"] == seed["class1_id"]
    assert body["class_code"] == "C1"
    assert body["room"] == "P101"


def test_get_session_detail_denied_for_other_lecturer(client, seed):
    token, session_id = _open_session(client, seed)
    other_token = login(client, "gv2@test.local", "gv123")
    resp = client.get(f"/sessions/{session_id}", headers=auth_headers(other_token))
    assert resp.status_code == 403


def test_classes_mine_filters_for_lecturer(client, seed):
    token = login(client, "gv1@test.local", "gv123")
    resp = client.get("/classes", params={"mine": True}, headers=auth_headers(token))
    assert resp.status_code == 200
    assert [c["id"] for c in resp.json()] == [seed["class1_id"]]


def test_classes_without_mine_still_scoped_to_own_classes(client, seed):
    """Giang vien chi thay lop minh day, ke ca khi khong truyen mine (truoc day lo toan truong)."""
    token = login(client, "gv1@test.local", "gv123")
    resp = client.get("/classes", headers=auth_headers(token))
    assert resp.status_code == 200
    assert [c["id"] for c in resp.json()] == [seed["class1_id"]]


def test_update_record_status(client, seed):
    token, session_id = _open_session(client, seed)
    manual_resp = client.post(
        f"/sessions/{session_id}/manual", json={"student_id": seed["sv1_id"]},
        headers=auth_headers(token),
    )
    record_id = manual_resp.json()["id"]

    resp = client.patch(
        f"/sessions/{session_id}/records/{record_id}",
        json={"status": "present", "reason": "SV xac nhan lai tai lop"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "present"


def test_update_record_rejects_invalid_status(client, seed):
    token, session_id = _open_session(client, seed)
    manual_resp = client.post(
        f"/sessions/{session_id}/manual", json={"student_id": seed["sv1_id"]},
        headers=auth_headers(token),
    )
    record_id = manual_resp.json()["id"]

    resp = client.patch(
        f"/sessions/{session_id}/records/{record_id}",
        json={"status": "invalid_status", "reason": "ly do bat ky"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 400


def test_update_record_requires_reason(client, seed):
    token, session_id = _open_session(client, seed)
    manual_resp = client.post(
        f"/sessions/{session_id}/manual", json={"student_id": seed["sv1_id"]},
        headers=auth_headers(token),
    )
    record_id = manual_resp.json()["id"]

    # thieu truong reason -> Pydantic tu choi truoc khi vao endpoint
    resp = client.patch(
        f"/sessions/{session_id}/records/{record_id}", json={"status": "present"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 422

    # co truong reason nhung rong/toan khoang trang -> endpoint tu choi
    resp = client.patch(
        f"/sessions/{session_id}/records/{record_id}",
        json={"status": "present", "reason": "   "},
        headers=auth_headers(token),
    )
    assert resp.status_code == 400


def test_update_record_denied_for_other_lecturer(client, seed):
    token, session_id = _open_session(client, seed)
    manual_resp = client.post(
        f"/sessions/{session_id}/manual", json={"student_id": seed["sv1_id"]},
        headers=auth_headers(token),
    )
    record_id = manual_resp.json()["id"]

    other_token = login(client, "gv2@test.local", "gv123")
    resp = client.patch(
        f"/sessions/{session_id}/records/{record_id}",
        json={"status": "present", "reason": "thu sua tu lop khac"},
        headers=auth_headers(other_token),
    )
    assert resp.status_code == 403


def test_update_record_creates_audit_with_old_and_new_status(client, seed):
    token, session_id = _open_session(client, seed)
    manual_resp = client.post(
        f"/sessions/{session_id}/manual", json={"student_id": seed["sv1_id"]},
        headers=auth_headers(token),
    )
    record_id = manual_resp.json()["id"]
    assert manual_resp.json()["status"] == "manual"

    resp = client.patch(
        f"/sessions/{session_id}/records/{record_id}",
        json={"status": "excused", "reason": "SV nop don xin phep co ly do"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "excused"

    audits = client.get(
        f"/sessions/{session_id}/records/{record_id}/audits", headers=auth_headers(token))
    assert audits.status_code == 200
    body = audits.json()
    assert len(body) == 1
    assert body[0]["old_status"] == "manual"
    assert body[0]["new_status"] == "excused"
    assert body[0]["reason"] == "SV nop don xin phep co ly do"


def test_update_record_still_works_after_session_closed(client, seed):
    # sv1 la SV duy nhat ghi danh lop1 (xem fixture seed); khong xac nhan gi ca
    # roi dong phien -> sv1 tu dong thanh "absent".
    token, session_id = _open_session(client, seed)
    close_resp = client.patch(f"/sessions/{session_id}/close", headers=auth_headers(token))
    assert close_resp.status_code == 200

    records = client.get(f"/sessions/{session_id}/records", headers=auth_headers(token)).json()
    absent_record = next(r for r in records if r["student_id"] == seed["sv1_id"])
    assert absent_record["status"] == "absent"

    resp = client.patch(
        f"/sessions/{session_id}/records/{absent_record['id']}",
        json={"status": "excused", "reason": "SV nop don phep sau buoi hoc"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "excused"


def test_audits_denied_for_other_lecturer(client, seed):
    token, session_id = _open_session(client, seed)
    manual_resp = client.post(
        f"/sessions/{session_id}/manual", json={"student_id": seed["sv1_id"]},
        headers=auth_headers(token),
    )
    record_id = manual_resp.json()["id"]
    client.patch(
        f"/sessions/{session_id}/records/{record_id}",
        json={"status": "present", "reason": "xac nhan lai"},
        headers=auth_headers(token),
    )

    other_token = login(client, "gv2@test.local", "gv123")
    resp = client.get(
        f"/sessions/{session_id}/records/{record_id}/audits", headers=auth_headers(other_token))
    assert resp.status_code == 403
