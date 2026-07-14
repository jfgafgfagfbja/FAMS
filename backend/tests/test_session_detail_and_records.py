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


def test_classes_without_mine_returns_all(client, seed):
    token = login(client, "gv1@test.local", "gv123")
    resp = client.get("/classes", headers=auth_headers(token))
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_update_record_status(client, seed):
    token, session_id = _open_session(client, seed)
    manual_resp = client.post(
        f"/sessions/{session_id}/manual", json={"student_id": seed["sv1_id"]},
        headers=auth_headers(token),
    )
    record_id = manual_resp.json()["id"]

    resp = client.patch(
        f"/sessions/{session_id}/records/{record_id}", json={"status": "present"},
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
        f"/sessions/{session_id}/records/{record_id}", json={"status": "invalid_status"},
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
        f"/sessions/{session_id}/records/{record_id}", json={"status": "present"},
        headers=auth_headers(other_token),
    )
    assert resp.status_code == 403
