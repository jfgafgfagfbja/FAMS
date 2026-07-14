from tests.conftest import auth_headers, login


def test_my_attendance_only_shows_own_enrolled_classes(client, seed):
    token = login(client, "sv1@test.local", "sv123")
    resp = client.get("/reports/my-attendance", headers=auth_headers(token))
    assert resp.status_code == 200
    data = resp.json()
    # sv1 chi ghi danh class1, chua co buoi diem danh nao dong -> 1 dong, 0 buoi
    assert len(data) == 1
    assert data[0]["class_code"] == "C1"
    assert data[0]["total_sessions"] == 0


def test_my_attendance_empty_when_not_enrolled(client, seed):
    token = login(client, "sv2@test.local", "sv123")
    resp = client.get("/reports/my-attendance", headers=auth_headers(token))
    assert resp.status_code == 200
    assert resp.json() == []


def test_lecturer_cannot_call_my_attendance(client, seed):
    token = login(client, "gv1@test.local", "gv123")
    resp = client.get("/reports/my-attendance", headers=auth_headers(token))
    assert resp.status_code == 403
