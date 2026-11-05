import io

from tests.conftest import consent_body, auth_headers, login


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
    resp = client.post(f"/students/{seed['sv2_id']}/consent", json=consent_body(), headers=auth_headers(token))
    assert resp.status_code == 403


def test_student_can_consent_for_self(client, seed):
    token = login(client, "sv1@test.local", "sv123")
    resp = client.post(f"/students/{seed['sv1_id']}/consent", json=consent_body(), headers=auth_headers(token))
    assert resp.status_code == 200
    assert resp.json()["consent_given"] is True

    me = client.get("/students/me", headers=auth_headers(token))
    assert me.json()["consent_given"] is True


def test_student_cannot_enroll_another_students_face(client, seed):
    token = login(client, "sv1@test.local", "sv123")
    # cho du sv2 da dong y, sv1 van khong duoc enroll ho sv2
    admin_token = login(client, "admin@test.local", "admin123")
    client.post(f"/students/{seed['sv2_id']}/consent", json=consent_body("paper"), headers=auth_headers(admin_token))

    resp = client.post(
        f"/faces/enroll/{seed['sv2_id']}", headers=auth_headers(token), files=_dummy_image(),
    )
    assert resp.status_code == 403


def test_lecturer_can_enroll_after_consent(client, seed):
    """Qua duoc cong consent/ownership; that bai o buoc doc anh (khong phai anh khuon mat that)
    nhung do la loi nghiep vu (ok=False), khong phai loi quyen truy cap."""
    admin_token = login(client, "admin@test.local", "admin123")
    client.post(f"/students/{seed['sv1_id']}/consent", json=consent_body("paper"), headers=auth_headers(admin_token))

    lecturer_token = login(client, "gv1@test.local", "gv123")
    resp = client.post(
        f"/faces/enroll/{seed['sv1_id']}", headers=auth_headers(lecturer_token), files=_dummy_image(),
    )
    assert resp.status_code == 200
    assert resp.json()["ok"] is False


# ---------------- Dong y bat buoc: noi dung co phien ban, ghi nhan cach dong y ----------------

def test_policy_text_comes_from_server_with_version(client, seed):
    token = login(client, "sv1@test.local", "sv123")
    body = client.get("/students/consent-policy", headers=auth_headers(token)).json()
    assert body["version"] and body["checkbox"]
    text = " ".join(body["items"]).lower()
    for must in ("mục đích", "rút đồng ý", "xác nhận trực tiếp"):
        assert must in text, must


def test_consent_requires_ticking_and_current_version(client, seed):
    token = auth_headers(login(client, "sv1@test.local", "sv123"))
    url = f"/students/{seed['sv1_id']}/consent"
    assert client.post(url, json={**consent_body(), "agreed": False}, headers=token).status_code == 400
    # Dong y voi noi dung cu (da doi) thi khong tinh.
    assert client.post(url, json={**consent_body(), "version": "2020-01"}, headers=token).status_code == 409


def test_self_consent_records_version_and_method(client, seed):
    token = auth_headers(login(client, "sv1@test.local", "sv123"))
    client.post(f"/students/{seed['sv1_id']}/consent", json=consent_body(), headers=token)
    me = client.get("/students/me", headers=token).json()
    assert me["consent_method"] == "self" and me["consent_recorded_by"] == "sv1@test.local"
    assert client.get("/auth/me", headers=token).json()["consent_outdated"] is False


def test_staff_can_only_record_a_signed_paper_form(client, seed):
    """Can bo khong duoc 'dong y thay' SV; chi nhap lai ban giay SV da ky, co ghi ten."""
    admin = auth_headers(login(client, "admin@test.local", "admin123"))
    url = f"/students/{seed['sv1_id']}/consent"
    assert client.post(url, json=consent_body("self"), headers=admin).status_code == 400
    resp = client.post(url, json=consent_body("paper"), headers=admin)
    assert resp.status_code == 200 and resp.json()["method"] == "paper"
    detail = client.get(f"/students/{seed['sv1_id']}", headers=admin).json()
    assert detail["consent_recorded_by"] == "admin@test.local"


def test_withdraw_deletes_all_face_data(client, db_session, seed):
    import numpy as np
    from app.db import models

    token = auth_headers(login(client, "sv1@test.local", "sv123"))
    client.post(f"/students/{seed['sv1_id']}/consent", json=consent_body(), headers=token)
    db_session.add(models.FaceEmbedding(student_id=seed["sv1_id"], embedding=np.ones(512).tolist(),
                                        status="approved"))
    db_session.commit()

    resp = client.post(f"/students/{seed['sv1_id']}/consent/withdraw", headers=token)
    assert resp.status_code == 200 and resp.json()["deleted"] == 1
    assert db_session.query(models.FaceEmbedding).filter_by(student_id=seed["sv1_id"]).count() == 0
    assert db_session.get(models.Student, seed["sv1_id"]).consent_given is False


def test_self_checkin_refused_without_consent(client, db_session, seed):
    from datetime import date

    gv = auth_headers(login(client, "gv1@test.local", "gv123"))
    session_id = client.post("/sessions", json={"schedule_id": seed["schedule1_id"],
                                                "session_date": str(date.today())}, headers=gv).json()["id"]
    sv = auth_headers(login(client, "sv1@test.local", "sv123"))
    resp = client.post(f"/sessions/{session_id}/self-checkin", data={},
                       files={"frame": ("f.jpg", b"x", "image/jpeg")}, headers=sv)
    assert resp.json()["status"] == "consent_required"


def test_class_scan_never_matches_student_without_consent(db_session, seed, monkeypatch):
    """Goi dung ham nhan dien cua camera lop (recognize_frame): chi thay bo do khuon mat bang
    mot khuon mat gia co vector trung khop, con truy van chon ung vien chay nguyen ban. Du con
    vector cu trong CSDL, SV chua dong y khong bao gio bi nhan ra."""
    from types import SimpleNamespace

    import numpy as np

    from app.core.config import settings
    from app.db import models
    from app.services import face_service

    vec = np.ones(512, dtype=np.float32) / np.sqrt(512)
    db_session.add(models.FaceEmbedding(student_id=seed["sv1_id"], embedding=vec.tolist(),
                                        status="approved"))
    db_session.commit()

    fake_face = SimpleNamespace(normed_embedding=vec, bbox=np.array([0, 0, 10, 10]), det_score=0.99)
    monkeypatch.setattr(face_service, "_decode_image", lambda data: np.zeros((20, 20, 3), np.uint8))
    monkeypatch.setattr(face_service, "get_engine",
                        lambda: SimpleNamespace(get=lambda img: [fake_face]))
    monkeypatch.setattr(settings, "ANTISPOOF_ENABLED", False)

    student = db_session.get(models.Student, seed["sv1_id"])
    student.consent_given = False
    db_session.commit()
    result = face_service.recognize_frame(db_session, b"x", seed["class1_id"])
    assert result and result[0]["student_id"] is None      # chua dong y: khong nhan ra

    student.consent_given = True
    db_session.commit()
    result = face_service.recognize_frame(db_session, b"x", seed["class1_id"])
    assert result[0]["student_id"] == seed["sv1_id"]        # dong y roi: nhan ra
