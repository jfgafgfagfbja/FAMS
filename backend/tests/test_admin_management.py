from tests.conftest import auth_headers, login


def test_admin_can_create_lecturer(client, seed):
    token = login(client, "admin@test.local", "admin123")
    resp = client.post("/lecturers", json={
        "email": "gv3@fams.edu.vn", "password": "pw123456",
        "full_name": "GV Ba", "lecturer_code": "GV03", "department": "CNTT",
    }, headers=auth_headers(token))
    assert resp.status_code == 200, resp.text
    assert resp.json()["lecturer_code"] == "GV03"


def test_lecturer_cannot_create_lecturer(client, seed):
    token = login(client, "gv1@test.local", "gv123")
    resp = client.post("/lecturers", json={
        "email": "gv4@fams.edu.vn", "password": "pw123456",
        "full_name": "GV Bon", "lecturer_code": "GV04",
    }, headers=auth_headers(token))
    assert resp.status_code == 403


def test_class_students_and_schedules_listing(client, seed):
    token = login(client, "admin@test.local", "admin123")
    resp = client.get(f"/classes/{seed['class1_id']}/students", headers=auth_headers(token))
    assert resp.status_code == 200
    assert [s["id"] for s in resp.json()] == [seed["sv1_id"]]

    resp = client.get(f"/classes/{seed['class1_id']}/schedules", headers=auth_headers(token))
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["room"] == "P101"


def test_enroll_and_unenroll_roundtrip(client, seed):
    token = login(client, "admin@test.local", "admin123")
    resp = client.post(
        f"/classes/{seed['class1_id']}/enroll/{seed['sv2_id']}", headers=auth_headers(token))
    assert resp.status_code == 200

    resp = client.get(f"/classes/{seed['class1_id']}/students", headers=auth_headers(token))
    assert {s["id"] for s in resp.json()} == {seed["sv1_id"], seed["sv2_id"]}

    resp = client.delete(
        f"/classes/{seed['class1_id']}/enroll/{seed['sv2_id']}", headers=auth_headers(token))
    assert resp.status_code == 200

    resp = client.get(f"/classes/{seed['class1_id']}/students", headers=auth_headers(token))
    assert [s["id"] for s in resp.json()] == [seed["sv1_id"]]


def test_lecturer_cannot_delete_class(client, seed):
    token = login(client, "gv1@test.local", "gv123")
    resp = client.delete(f"/classes/{seed['class1_id']}", headers=auth_headers(token))
    assert resp.status_code == 403
