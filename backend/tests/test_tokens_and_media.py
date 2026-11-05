"""Refresh token (app mobile), URL anh co chu ky, du lieu khuon mat cua chinh SV."""
import os
import time as time_module

import cv2
import numpy as np

from app.core import media
from app.core.config import settings
from app.db import models
from app.services import antispoof_service, face_service
from tests.conftest import consent_body, auth_headers, login


def _login_full(client, email, password):
    resp = client.post("/auth/login", data={"username": email, "password": password})
    assert resp.status_code == 200
    return resp.json()


# ---------------- Refresh token ----------------

def test_login_returns_refresh_token(client, seed):
    body = _login_full(client, "sv1@test.local", "sv123")
    assert body["refresh_token"]
    assert body["expires_in"] == settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60


def test_refresh_rotates_and_old_token_reuse_revokes_all(client, seed):
    first = _login_full(client, "sv1@test.local", "sv123")
    resp = client.post("/auth/refresh", json={"refresh_token": first["refresh_token"]})
    assert resp.status_code == 200
    second = resp.json()
    assert second["refresh_token"] != first["refresh_token"]
    assert client.get("/students/me", headers=auth_headers(second["access_token"])).status_code == 200

    # Dung lai refresh token cu -> nghi bi lo: tu choi va thu hoi luon token moi.
    assert client.post("/auth/refresh", json={"refresh_token": first["refresh_token"]}).status_code == 401
    assert client.post("/auth/refresh", json={"refresh_token": second["refresh_token"]}).status_code == 401


def test_logout_revokes_refresh_token(client, seed):
    body = _login_full(client, "sv1@test.local", "sv123")
    resp = client.post("/auth/logout", json={"refresh_token": body["refresh_token"]},
                       headers=auth_headers(body["access_token"]))
    assert resp.status_code == 200
    assert client.post("/auth/refresh", json={"refresh_token": body["refresh_token"]}).status_code == 401


def test_reset_password_revokes_refresh_tokens(client, seed, db_session):
    from datetime import datetime, timedelta
    from app.core.security import hash_password

    body = _login_full(client, "sv1@test.local", "sv123")
    user = db_session.query(models.User).filter_by(email="sv1@test.local").first()
    db_session.add(models.PasswordReset(user_id=user.id, otp_hash=hash_password("123456"),
                                        expires_at=datetime.utcnow() + timedelta(minutes=5)))
    db_session.commit()
    assert client.post("/auth/reset-password", json={
        "email": "sv1@test.local", "otp": "123456", "new_password": "matkhaumoi1"}).status_code == 200
    assert client.post("/auth/refresh", json={"refresh_token": body["refresh_token"]}).status_code == 401


def test_refresh_with_garbage_token(client, seed):
    assert client.post("/auth/refresh", json={"refresh_token": "khong-hop-le"}).status_code == 401


# ---------------- URL anh co chu ky ----------------

def _write_evidence(tmp_path, monkeypatch, rel="7/anh.jpg"):
    monkeypatch.setattr(settings, "EVIDENCE_DIR", str(tmp_path))
    full = tmp_path / rel
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_bytes(b"\xff\xd8fake-jpeg")
    return f"/evidence/{rel}"


def test_signed_media_url_served(client, tmp_path, monkeypatch):
    path = _write_evidence(tmp_path, monkeypatch)
    signed = media.sign_media_path(path)
    resp = client.get(signed)
    assert resp.status_code == 200
    assert resp.content == b"\xff\xd8fake-jpeg"


def test_unsigned_or_tampered_media_rejected(client, tmp_path, monkeypatch):
    path = _write_evidence(tmp_path, monkeypatch)
    assert client.get(path).status_code == 403
    signed = media.sign_media_path(path)
    assert client.get(signed.replace("anh.jpg", "khac.jpg")).status_code == 403


def test_expired_media_url_rejected(client, tmp_path, monkeypatch):
    path = _write_evidence(tmp_path, monkeypatch)
    exp = int(time_module.time()) - 10
    sig = media._signature(path, exp)
    assert client.get(f"{path}?exp={exp}&sig={sig}").status_code == 403


def test_media_path_traversal_blocked(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "EVIDENCE_DIR", str(tmp_path / "evidence"))
    assert media.media_file_path("../secret.txt") is None


# ---------------- Anh doi chieu khi duyet + du lieu cua toi ----------------

class _FakeFace:
    def __init__(self, embedding):
        self.bbox = np.array([20, 20, 180, 180], dtype=np.float32)
        self.normed_embedding = embedding


def _enroll_one(client, seed, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "EVIDENCE_DIR", str(tmp_path))
    emb = np.random.RandomState(3).rand(512).astype(np.float32)
    emb /= np.linalg.norm(emb)
    face = _FakeFace(emb)
    monkeypatch.setattr(face_service, "get_engine", lambda: type("E", (), {"get": lambda self, img: [face]})())
    monkeypatch.setattr(face_service, "_check_quality", lambda img, f: None)
    monkeypatch.setattr(antispoof_service, "check_liveness", lambda img, bbox: (True, 0.9))

    token = login(client, "sv1@test.local", "sv123")
    client.post(f"/students/{seed['sv1_id']}/consent", json=consent_body(), headers=auth_headers(token))
    image = cv2.imencode(".jpg", np.full((200, 200, 3), 128, dtype=np.uint8))[1].tobytes()
    resp = client.post(f"/faces/enroll/{seed['sv1_id']}", headers=auth_headers(token),
                       files={"images": ("front.jpg", image, "image/jpeg")})
    assert resp.json()["ok"] is True
    return token


def test_review_image_saved_then_deleted_on_approve(client, seed, monkeypatch, tmp_path):
    _enroll_one(client, seed, monkeypatch, tmp_path)
    admin = auth_headers(login(client, "admin@test.local", "admin123"))
    pending = client.get("/faces/pending", headers=admin).json()
    assert len(pending) == 1
    image_url = pending[0]["source_image"]
    assert "sig=" in image_url
    assert client.get(image_url).status_code == 200

    raw_path = image_url.split("?")[0]
    file_on_disk = os.path.join(str(tmp_path), raw_path[len("/evidence/"):])
    assert os.path.isfile(file_on_disk)

    assert client.patch(f"/faces/{pending[0]['id']}/approve", headers=admin).status_code == 200
    assert not os.path.isfile(file_on_disk)


def test_student_views_and_deletes_own_face_data(client, seed, monkeypatch, tmp_path):
    token = _enroll_one(client, seed, monkeypatch, tmp_path)
    mine = client.get("/faces/mine", headers=auth_headers(token)).json()
    assert [m["status"] for m in mine] == ["pending"]
    assert "embedding" not in mine[0]

    me = client.get("/auth/me", headers=auth_headers(token)).json()
    assert me["face_status"] == "pending"

    resp = client.delete("/faces/mine", headers=auth_headers(token))
    assert resp.json()["deleted"] == 1
    assert client.get("/faces/mine", headers=auth_headers(token)).json() == []
    assert client.get("/students/me", headers=auth_headers(token)).json()["consent_given"] is False


def test_face_enrolled_only_counts_approved(client, seed, monkeypatch, tmp_path):
    _enroll_one(client, seed, monkeypatch, tmp_path)
    admin = auth_headers(login(client, "admin@test.local", "admin123"))
    student = client.get(f"/students/{seed['sv1_id']}", headers=admin).json()
    assert student["face_enrolled"] is False
    assert student["face_status"] == "pending"
