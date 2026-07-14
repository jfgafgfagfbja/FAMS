import io

from tests.conftest import auth_headers, login


def _dummy_image():
    return {"images": ("face.jpg", io.BytesIO(b"not-a-real-image"), "image/jpeg")}


def test_enroll_blocked_without_consent(client, seed):
    token = login(client, "sv1@test.local", "sv123")
    resp = client.post(
        f"/faces/enroll/{seed['sv1_id']}", headers=auth_headers(token), files=_dummy_image(),
    )
    assert resp.status_code == 400
    assert "dong y" in resp.json()["detail"].lower()


def test_student_cannot_consent_for_another_student(client, seed):
    token = login(client, "sv1@test.local", "sv123")
    resp = client.post(f"/students/{seed['sv2_id']}/consent", headers=auth_headers(token))
    assert resp.status_code == 403


def test_student_can_consent_for_self(client, seed):
    token = login(client, "sv1@test.local", "sv123")
    resp = client.post(f"/students/{seed['sv1_id']}/consent", headers=auth_headers(token))
    assert resp.status_code == 200
    assert resp.json()["consent_given"] is True

    me = client.get("/students/me", headers=auth_headers(token))
    assert me.json()["consent_given"] is True


def test_student_cannot_enroll_another_students_face(client, seed):
    token = login(client, "sv1@test.local", "sv123")
    # cho du sv2 da dong y, sv1 van khong duoc enroll ho sv2
    admin_token = login(client, "admin@test.local", "admin123")
    client.post(f"/students/{seed['sv2_id']}/consent", headers=auth_headers(admin_token))

    resp = client.post(
        f"/faces/enroll/{seed['sv2_id']}", headers=auth_headers(token), files=_dummy_image(),
    )
    assert resp.status_code == 403


def test_lecturer_can_enroll_after_consent(client, seed):
    """Qua duoc cong consent/ownership; that bai o buoc doc anh (khong phai anh khuon mat that)
    nhung do la loi nghiep vu (ok=False), khong phai loi quyen truy cap."""
    admin_token = login(client, "admin@test.local", "admin123")
    client.post(f"/students/{seed['sv1_id']}/consent", headers=auth_headers(admin_token))

    lecturer_token = login(client, "gv1@test.local", "gv123")
    resp = client.post(
        f"/faces/enroll/{seed['sv1_id']}", headers=auth_headers(lecturer_token), files=_dummy_image(),
    )
    assert resp.status_code == 200
    assert resp.json()["ok"] is False
