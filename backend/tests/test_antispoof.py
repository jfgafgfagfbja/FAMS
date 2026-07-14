"""Test anti-spoofing: khong can model that, mock check_liveness (va detection engine)."""
from datetime import date

import cv2
import numpy as np
import pytest

from app.db import models
from app.services import antispoof_service, face_service
from tests.conftest import auth_headers, login


class _FakeFace:
    def __init__(self, bbox, embedding):
        self.bbox = bbox
        self.normed_embedding = embedding


class _FakeEngine:
    def __init__(self, face):
        self._face = face

    def get(self, img):
        return [self._face]


def _tiny_jpeg_bytes() -> bytes:
    return cv2.imencode(".jpg", np.zeros((20, 20, 3), dtype=np.uint8))[1].tobytes()


@pytest.fixture()
def sv1_embedding(db_session, seed):
    """Tao 1 face_embedding that cho sv1, dung lam gallery de so khop."""
    emb = np.random.rand(512).astype(np.float32)
    emb = emb / np.linalg.norm(emb)
    db_session.add(models.FaceEmbedding(student_id=seed["sv1_id"], embedding=emb.tolist()))
    db_session.commit()
    return emb


# ---------------- Muc service: face_service.recognize_frame ----------------

def test_recognize_frame_marks_spoof_but_still_identifies_student(
    db_session, seed, sv1_embedding, monkeypatch,
):
    bbox = np.array([0, 0, 20, 20], dtype=np.float32)
    fake_face = _FakeFace(bbox, sv1_embedding)
    monkeypatch.setattr(face_service, "get_engine", lambda: _FakeEngine(fake_face))
    monkeypatch.setattr(antispoof_service, "check_liveness", lambda img, bbox: (False, 0.12))

    results = face_service.recognize_frame(db_session, _tiny_jpeg_bytes(), seed["class1_id"])

    assert len(results) == 1
    assert results[0]["is_spoof"] is True
    assert results[0]["liveness_score"] == 0.12
    assert results[0]["student_id"] == seed["sv1_id"]


def test_recognize_frame_marks_real_face(db_session, seed, sv1_embedding, monkeypatch):
    bbox = np.array([0, 0, 20, 20], dtype=np.float32)
    fake_face = _FakeFace(bbox, sv1_embedding)
    monkeypatch.setattr(face_service, "get_engine", lambda: _FakeEngine(fake_face))
    monkeypatch.setattr(antispoof_service, "check_liveness", lambda img, bbox: (True, 0.93))

    results = face_service.recognize_frame(db_session, _tiny_jpeg_bytes(), seed["class1_id"])

    assert results[0]["is_spoof"] is False
    assert results[0]["student_id"] == seed["sv1_id"]


# ---------------- Muc endpoint: POST /sessions/{id}/recognize ----------------

def _open_session(client, seed):
    token = login(client, "gv1@test.local", "gv123")
    resp = client.post(
        "/sessions",
        json={"schedule_id": seed["schedule1_id"], "session_date": str(date.today())},
        headers=auth_headers(token),
    )
    return token, resp.json()["id"]


def test_spoof_does_not_create_attendance_record(client, seed, monkeypatch):
    token, session_id = _open_session(client, seed)

    monkeypatch.setattr(face_service, "recognize_frame", lambda db, data, class_id: [
        {"student_id": seed["sv1_id"], "confidence": 0.9, "bbox": [0, 0, 10, 10],
         "is_spoof": True, "liveness_score": 0.1},
    ])

    resp = client.post(
        f"/sessions/{session_id}/recognize",
        files={"frame": ("frame.jpg", b"fake", "image/jpeg")},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body[0]["status"] == "spoof"
    assert body[0]["liveness_score"] == 0.1
    assert body[0]["evidence_image"]  # van luu anh bang chung de admin xem lai

    records = client.get(f"/sessions/{session_id}/records", headers=auth_headers(token))
    assert records.json() == []


def test_real_face_creates_attendance_record_after_confirm_frames(client, seed, monkeypatch):
    """Mac dinh CONFIRM_FRAMES=2: frame dau tra ve "confirming", frame thu 2 moi ghi record."""
    token, session_id = _open_session(client, seed)

    monkeypatch.setattr(face_service, "recognize_frame", lambda db, data, class_id: [
        {"student_id": seed["sv1_id"], "confidence": 0.9, "bbox": [0, 0, 10, 10],
         "is_spoof": False, "liveness_score": 0.95},
    ])

    resp1 = client.post(
        f"/sessions/{session_id}/recognize",
        files={"frame": ("frame.jpg", b"fake", "image/jpeg")},
        headers=auth_headers(token),
    )
    assert resp1.status_code == 200
    body1 = resp1.json()[0]
    assert body1["status"] == "confirming"
    assert body1["confirm_count"] == 1
    assert body1["confirm_needed"] == 2

    records_after_1 = client.get(f"/sessions/{session_id}/records", headers=auth_headers(token))
    assert records_after_1.json() == []

    resp2 = client.post(
        f"/sessions/{session_id}/recognize",
        files={"frame": ("frame.jpg", b"fake", "image/jpeg")},
        headers=auth_headers(token),
    )
    assert resp2.status_code == 200
    assert resp2.json()[0]["status"] == "recognized"

    records = client.get(f"/sessions/{session_id}/records", headers=auth_headers(token))
    assert len(records.json()) == 1
    assert records.json()[0]["student_id"] == seed["sv1_id"]


# ---------------- check_liveness khi chua co model ----------------

def test_check_liveness_defaults_to_real_when_model_missing(monkeypatch):
    monkeypatch.setattr(antispoof_service, "_session", None)
    monkeypatch.setattr(antispoof_service, "_load_attempted", False)
    monkeypatch.setattr(
        "app.core.config.settings.ANTISPOOF_MODEL_PATH", "/duong/dan/khong/ton/tai.onnx")

    is_real, score = antispoof_service.check_liveness(
        np.zeros((20, 20, 3), dtype=np.uint8), np.array([0, 0, 20, 20]))

    assert is_real is True
    assert score == 1.0
