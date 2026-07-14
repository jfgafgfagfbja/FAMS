"""Face Service — trai tim AI cua FAMS.

Enrollment: anh -> kiem tra chat luong -> embedding 512d -> luu DB.
Recognition: frame -> detect nhieu mat -> embedding -> so khop voi SV trong lop.

Dung InsightFace buffalo_l (SCRFD detector + ArcFace). Chay CPU qua ONNX Runtime.
"""
import io

import cv2
import numpy as np
from insightface.app import FaceAnalysis
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import models
from app.services import antispoof_service

MIN_FACE_SIZE = 112          # pixel, mat nho hon -> tu choi
MIN_BRIGHTNESS = 40          # do sang trung binh toi thieu
MIN_BLUR_SCORE = 60.0        # variance of Laplacian, thap hon -> anh mo

_engine: FaceAnalysis | None = None


def get_engine() -> FaceAnalysis:
    """Lazy-load model (lan dau tai ~300MB)."""
    global _engine
    if _engine is None:
        _engine = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
        _engine.prepare(ctx_id=0, det_size=(640, 640))
    return _engine


def _decode_image(data: bytes) -> np.ndarray:
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Khong doc duoc anh")
    return img


def _check_quality(img: np.ndarray, face) -> str | None:
    """Tra ve thong bao loi neu anh khong dat, None neu OK."""
    x1, y1, x2, y2 = face.bbox.astype(int)
    if min(x2 - x1, y2 - y1) < MIN_FACE_SIZE:
        return "Khuon mat qua nho, hay tien gan camera"
    crop = img[max(y1, 0):y2, max(x1, 0):x2]
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    if gray.mean() < MIN_BRIGHTNESS:
        return "Anh qua toi"
    if cv2.Laplacian(gray, cv2.CV_64F).var() < MIN_BLUR_SCORE:
        return "Anh bi mo, hay giu yen camera"
    return None


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8))


# ---------------- ENROLLMENT ----------------

def enroll_face(db: Session, student_id: int, image_bytes: bytes) -> tuple[bool, str]:
    """Xu ly 1 anh dang ky. Tra ve (ok, message)."""
    img = _decode_image(image_bytes)
    faces = get_engine().get(img)

    if len(faces) == 0:
        return False, "Khong tim thay khuon mat"
    if len(faces) > 1:
        return False, "Co nhieu hon 1 khuon mat trong anh"

    face = faces[0]
    err = _check_quality(img, face)
    if err:
        return False, err

    if settings.ANTISPOOF_ENABLED:
        is_real, liveness_score = antispoof_service.check_liveness(img, face.bbox)
        if not is_real:
            return False, f"Anh nghi la gia mao (anh in/anh chup lai), diem that: {liveness_score}"

    emb = face.normed_embedding.astype(np.float32)

    # Kiem tra trung voi sinh vien khac
    others = (
        db.query(models.FaceEmbedding)
        .filter(models.FaceEmbedding.student_id != student_id)
        .all()
    )
    for other in others:
        if cosine_similarity(emb, np.array(other.embedding)) > settings.DUPLICATE_THRESHOLD:
            return False, (
                f"Khuon mat qua giong sinh vien id={other.student_id} da dang ky. "
                "Can admin xac minh."
            )

    db.add(models.FaceEmbedding(student_id=student_id, embedding=emb.tolist()))
    db.commit()
    return True, "Dang ky thanh cong"


# ---------------- RECOGNITION ----------------

def recognize_frame(
    db: Session, image_bytes: bytes, class_id: int
) -> list[dict]:
    """Nhan dien tat ca khuon mat trong frame, chi so khop voi SV thuoc lop class_id.

    Moi khuon mat deu duoc kiem tra liveness (chong gia mao). Van co gang nhan dien
    danh tinh ke ca khi bi nghi gia mao (de admin biet ai co gang gian lan) - noi goi
    (api/sessions.py) se quyet dinh khong ghi attendance record khi is_spoof=True.

    Tra ve list: [{student_id | None, confidence, bbox, is_spoof, liveness_score}]
    """
    img = _decode_image(image_bytes)
    faces = get_engine().get(img)
    if not faces:
        return []

    # Lay embedding cua SV trong lop (gioi han pham vi tim kiem)
    rows = (
        db.query(models.FaceEmbedding, models.Enrollment.student_id)
        .join(models.Enrollment,
              models.Enrollment.student_id == models.FaceEmbedding.student_id)
        .filter(models.Enrollment.class_id == class_id)
        .all()
    )
    gallery = np.array([np.array(r[0].embedding) for r in rows]) if rows else None
    gallery_ids = [r[1] for r in rows]

    results = []
    for face in faces:
        is_real, liveness_score = (True, 1.0)
        if settings.ANTISPOOF_ENABLED:
            is_real, liveness_score = antispoof_service.check_liveness(img, face.bbox)

        if gallery is None:
            results.append({
                "student_id": None, "confidence": 0.0,
                "bbox": face.bbox.astype(int).tolist(),
                "is_spoof": not is_real, "liveness_score": liveness_score,
            })
            continue

        emb = face.normed_embedding.astype(np.float32)
        sims = gallery @ emb / (
            np.linalg.norm(gallery, axis=1) * np.linalg.norm(emb) + 1e-8
        )
        best = int(np.argmax(sims))
        conf = float(sims[best])
        results.append({
            "student_id": gallery_ids[best] if conf >= settings.RECOGNITION_THRESHOLD else None,
            "confidence": round(conf, 3),
            "bbox": face.bbox.astype(int).tolist(),
            "is_spoof": not is_real,
            "liveness_score": liveness_score,
        })
    return results
