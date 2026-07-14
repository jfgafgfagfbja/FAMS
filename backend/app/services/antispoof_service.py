"""Anti-spoofing — chong gia mao bang anh in / anh chup man hinh dien thoai / video phat lai.

Dung MiniFASNetV2 (Silent-Face-Anti-Spoofing) chay ONNX Runtime, giong cach lazy-load
model trong face_service.get_engine().

Tai model o dau:
    Repo goc: https://github.com/minivision-ai/Silent-Face-Anti-Spoofing
    File can: resources/anti_spoof_models/2.7_80x80_MiniFASNetV2.pth
    Repo goc luu bang PyTorch (.pth), can convert sang ONNX (vi du bang torch.onnx.export
    voi input shape (1, 3, 80, 80)) hoac tim ban ONNX da convert san tren Hugging Face /
    GitHub (tim tu khoa "MiniFASNetV2 onnx" hoac "silent face anti spoofing onnx").

Dat file .onnx vao:
    backend/models/2.7_80x80_MiniFASNetV2.onnx
    (thu muc backend/models/ da duoc tao san, xem backend/models/README.md)
    Neu muon dat noi khac, sua ANTISPOOF_MODEL_PATH trong .env.

Neu file model chua co: check_liveness() luon tra ve (True, 1.0) - tuc bo qua kiem tra,
khong chan luong nhan dien/dang ky, chi log 1 dong warning luc goi lan dau.
"""
import logging
import os

import cv2
import numpy as np
import onnxruntime as ort

from app.core.config import settings

logger = logging.getLogger(__name__)

SCALE = 2.7            # he so mo rong bbox theo chuan model 2.7_80x80
INPUT_SIZE = 80        # kich thuoc dau vao model (80x80)
REAL_LABEL = 1         # nhan "mat that" trong output 3 lop cua model

_session: ort.InferenceSession | None = None
_load_attempted = False


def _load_session() -> ort.InferenceSession | None:
    """Lazy-load model ONNX. Tra ve None neu file khong ton tai hoac loi (khong crash app)."""
    global _session, _load_attempted
    if _load_attempted:
        return _session
    _load_attempted = True

    if not os.path.isfile(settings.ANTISPOOF_MODEL_PATH):
        logger.warning(
            "Khong tim thay model anti-spoofing tai '%s'. Bo qua kiem tra liveness "
            "(xem huong dan tai model trong app/services/antispoof_service.py).",
            settings.ANTISPOOF_MODEL_PATH,
        )
        return None

    try:
        _session = ort.InferenceSession(
            settings.ANTISPOOF_MODEL_PATH, providers=["CPUExecutionProvider"])
    except Exception:
        logger.warning(
            "Khong the tai model anti-spoofing tai '%s' (file loi/khong dung dinh dang). "
            "Bo qua kiem tra liveness.", settings.ANTISPOOF_MODEL_PATH, exc_info=True)
        _session = None
    return _session


def warm_up() -> None:
    """Goi luc khoi dong app (main.py lifespan) de log canh bao ngay neu model chua co,
    thay vi doi den request dau tien moi bao."""
    if settings.ANTISPOOF_ENABLED:
        _load_session()


def _crop_with_margin(img: np.ndarray, bbox: np.ndarray, scale: float, out_size: int) -> np.ndarray:
    """Crop mat theo bbox voi vien mo rong scale lan, resize ve out_size x out_size.

    Giu nguyen thuat toan cua Silent-Face-Anti-Spoofing (CropImage._get_new_box):
    mo rong tu tam bbox, neu vuot bien anh thi keo lai cho vua khung.
    """
    src_h, src_w = img.shape[:2]
    x1, y1, x2, y2 = bbox.astype(float)
    box_w, box_h = x2 - x1, y2 - y1

    eff_scale = min((src_h - 1) / box_h, min((src_w - 1) / box_w, scale))
    new_w, new_h = box_w * eff_scale, box_h * eff_scale
    center_x, center_y = x1 + box_w / 2, y1 + box_h / 2

    left, top = center_x - new_w / 2, center_y - new_h / 2
    right, bottom = center_x + new_w / 2, center_y + new_h / 2

    if left < 0:
        right -= left
        left = 0
    if top < 0:
        bottom -= top
        top = 0
    if right > src_w - 1:
        left -= right - (src_w - 1)
        right = src_w - 1
    if bottom > src_h - 1:
        top -= bottom - (src_h - 1)
        bottom = src_h - 1

    crop = img[int(top):int(bottom) + 1, int(left):int(right) + 1]
    return cv2.resize(crop, (out_size, out_size))


def _softmax(x: np.ndarray) -> np.ndarray:
    e = np.exp(x - np.max(x))
    return e / e.sum()


def check_liveness(img: np.ndarray, bbox: np.ndarray) -> tuple[bool, float]:
    """Kiem tra 1 khuon mat la that hay gia (anh in/man hinh/video phat lai).

    Tra ve (is_real, score). Neu model chua duoc tai (file khong ton tai), luon
    tra ve (True, 1.0) - bo qua kiem tra thay vi chan luong nhan dien/dang ky.
    """
    session = _load_session()
    if session is None:
        return True, 1.0

    face = _crop_with_margin(img, bbox, SCALE, INPUT_SIZE)
    blob = face.astype(np.float32) / 255.0
    blob = np.transpose(blob, (2, 0, 1))[np.newaxis, ...]  # NCHW

    input_name = session.get_inputs()[0].name
    raw_output = session.run(None, {input_name: blob})[0][0]  # (3,)
    probs = _softmax(raw_output)

    label = int(np.argmax(probs))
    score = float(probs[REAL_LABEL])
    is_real = label == REAL_LABEL and score >= settings.ANTISPOOF_THRESHOLD
    return is_real, round(score, 3)
