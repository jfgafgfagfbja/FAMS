"""Face Service — trai tim AI cua FAMS.

Enrollment: anh -> kiem tra chat luong -> embedding 512d -> luu DB.
Recognition: frame -> detect nhieu mat -> embedding -> so khop voi SV trong lop.

Dung InsightFace buffalo_l (SCRFD detector + ArcFace). Chay CPU qua ONNX Runtime.
"""
import os
import uuid

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

    # Kiem tra trung voi sinh vien khac: de pgvector tim embedding gan nhat qua
    # toan tu <=> (cosine distance) thay vi tai het ve tinh bang numpy.
    # similarity = 1 - distance. Chi so sanh voi embedding da duoc admin duyet -
    # embedding dang cho duyet/da tu choi cua nguoi khac chua du tin cay de dung
    # lam can cu bao trung.
    distance = models.FaceEmbedding.embedding.cosine_distance(emb.tolist())
    nearest = (
        db.query(models.FaceEmbedding.student_id, distance.label("distance"))
        .filter(models.FaceEmbedding.student_id != student_id,
                models.FaceEmbedding.status == "approved")
        .order_by(distance)
        .first()
    )
    if nearest is not None:
        other_student_id, dist = nearest
        if 1 - dist > settings.DUPLICATE_THRESHOLD:
            return False, (
                f"Khuon mat qua giong sinh vien id={other_student_id} da dang ky. "
                "Can admin xac minh."
            )

    # Embedding moi luon o trang thai "pending" - chi admin/P.CTSV duyet (PATCH
    # /faces/{id}/approve) moi duoc dung de nhan dien (xem recognize_frame). Anh mat
    # da cat duoc luu TAM de nguoi duyet doi chieu, xoa khi duyet/tu choi.
    db.add(models.FaceEmbedding(student_id=student_id, embedding=emb.tolist(),
                                status="pending",
                                source_image=_save_review_crop(img, face.bbox, student_id)))
    db.commit()
    return True, "Da luu anh, dang cho can bo duyet"


def _save_review_crop(img: np.ndarray, bbox, student_id: int) -> str:
    """Cat vung mat (noi rong 30% moi phia) luu vao EVIDENCE_DIR/faces/<student_id>/."""
    h, w = img.shape[:2]
    x1, y1, x2, y2 = bbox.astype(int)
    pad_x, pad_y = int((x2 - x1) * 0.3), int((y2 - y1) * 0.3)
    crop = img[max(y1 - pad_y, 0):min(y2 + pad_y, h), max(x1 - pad_x, 0):min(x2 + pad_x, w)]
    if crop.size == 0:
        crop = img
    ok, buf = cv2.imencode(".jpg", crop, [cv2.IMWRITE_JPEG_QUALITY, 85])
    if not ok:
        return ""
    rel_dir = os.path.join("faces", str(student_id))
    os.makedirs(os.path.join(settings.EVIDENCE_DIR, rel_dir), exist_ok=True)
    filename = f"{uuid.uuid4().hex}.jpg"
    with open(os.path.join(settings.EVIDENCE_DIR, rel_dir, filename), "wb") as f:
        f.write(buf.tobytes())
    return f"/evidence/faces/{student_id}/{filename}"


# ---------------- SELF CHECK-IN (SV tu chup selfie) ----------------

def recognize_self(db: Session, image_bytes: bytes, student_id: int) -> dict:
    """Nhan dien anh selfie SV tu chup, CHI so khop voi embedding da duyet cua
    CHINH student_id do (khac recognize_frame - so voi ca lop) - de tranh 1 SV
    chup ho/gia mao danh tinh nguoi khac trong luong tu diem danh.

    Tra ve dict: {status, confidence, liveness_score, bbox}
    status: no_face | multiple_faces | spoof | not_matched | matched
    """
    img = _decode_image(image_bytes)
    faces = get_engine().get(img)

    if len(faces) == 0:
        return {"status": "no_face", "confidence": 0.0, "liveness_score": None, "bbox": None}
    if len(faces) > 1:
        return {"status": "multiple_faces", "confidence": 0.0, "liveness_score": None, "bbox": None}

    face = faces[0]
    bbox = face.bbox.astype(int).tolist()

    is_real, liveness_score = (True, 1.0)
    if settings.ANTISPOOF_ENABLED:
        is_real, liveness_score = antispoof_service.check_liveness(img, face.bbox)
    if not is_real:
        return {"status": "spoof", "confidence": 0.0,
                "liveness_score": liveness_score, "bbox": bbox}

    emb = face.normed_embedding.astype(np.float32)
    distance = models.FaceEmbedding.embedding.cosine_distance(emb.tolist())
    nearest = (
        db.query(distance.label("distance"))
        .filter(models.FaceEmbedding.student_id == student_id,
                models.FaceEmbedding.status == "approved")
        .order_by(distance)
        .first()
    )
    if nearest is None:
        # Chua co embedding nao duoc duyet cho SV nay
        return {"status": "not_matched", "confidence": 0.0,
                "liveness_score": liveness_score, "bbox": bbox}

    conf = round(1 - nearest[0], 3)
    if conf < settings.RECOGNITION_THRESHOLD:
        return {"status": "not_matched", "confidence": conf,
                "liveness_score": liveness_score, "bbox": bbox}

    return {"status": "matched", "confidence": conf,
            "liveness_score": liveness_score, "bbox": bbox}


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

    results = []
    for face in faces:
        is_real, liveness_score = (True, 1.0)
        if settings.ANTISPOOF_ENABLED:
            is_real, liveness_score = antispoof_service.check_liveness(img, face.bbox)

        # Tim embedding gan nhat (cosine distance qua toan tu <=>, dung index HNSW)
        # chi trong so SV thuoc lop nay va CHI trong embedding da duoc admin duyet -
        # embedding cho duyet/bi tu choi khong duoc dung de nhan dien diem danh.
        emb = face.normed_embedding.astype(np.float32)
        distance = models.FaceEmbedding.embedding.cosine_distance(emb.tolist())
        match = (
            db.query(models.Enrollment.student_id, distance.label("distance"))
            .join(models.FaceEmbedding,
                  models.FaceEmbedding.student_id == models.Enrollment.student_id)
            .filter(models.Enrollment.class_id == class_id,
                    models.FaceEmbedding.status == "approved")
            .order_by(distance)
            .first()
        )

        if match is None:
            results.append({
                "student_id": None, "confidence": 0.0,
                "bbox": face.bbox.astype(int).tolist(),
                "is_spoof": not is_real, "liveness_score": liveness_score,
            })
            continue

        student_id, dist = match
        conf = round(1 - dist, 3)
        results.append({
            "student_id": student_id if conf >= settings.RECOGNITION_THRESHOLD else None,
            "confidence": conf,
            "bbox": face.bbox.astype(int).tolist(),
            "is_spoof": not is_real,
            "liveness_score": liveness_score,
        })
    return results
