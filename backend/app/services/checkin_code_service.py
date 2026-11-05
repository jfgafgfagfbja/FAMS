"""Ma diem danh doi theo chu ky, dung de xac nhan sinh vien co mat dung phong hoc.

GPS khong phan biet duoc hai phong canh nhau, nen muon chac chan SV ngoi trong phong
thi can mot tin hieu chi co trong phong moi thay duoc. Cach lam o day: giang vien chieu
len man hinh/may chieu mot ma QR tu doi sau moi CHECKIN_QR_ROTATE_SECONDS giay; SV quet
ma do khi tu diem danh.

Ma khong luu vao CSDL ma duoc tinh tu (id phien + o thoi gian) bang HMAC voi SECRET_KEY,
giong cach ky URL anh bang chung. Nho vay:
  - Khong can bang moi, khong can don rac.
  - Chup man hinh gui qua nhom chat thi het han sau toi da 2 chu ky.
  - Ma cua phien nay khong dung duoc cho phien khac.

Chap nhan ca o thoi gian truoc do mot nhip de SV quet cham vai giay hoac dong ho lech
mot chut van diem danh duoc.
"""
import hashlib
import hmac
import math
import time
from dataclasses import dataclass

from app.core.config import settings

QR_PREFIX = "FAMS"


def _window(at: float | None = None) -> int:
    """So thu tu cua o thoi gian hien tai."""
    now = time.time() if at is None else at
    return int(now // settings.CHECKIN_QR_ROTATE_SECONDS)


def _digest(session_id: int, window: int) -> str:
    message = f"{session_id}|{window}".encode()
    return hmac.new(settings.SECRET_KEY.encode(), message, hashlib.sha256).hexdigest()


def _signature(session_id: int, window: int) -> str:
    return _digest(session_id, window)[:12]


def _digits(session_id: int, window: int) -> str:
    """Ma 6 chu so cho cung o thoi gian - de SV go tay khi khong quet duoc QR
    (ngoi cuoi giang duong, camera mo, may chieu nhoe)."""
    return f"{int(_digest(session_id, window)[:8], 16) % 1_000_000:06d}"


@dataclass
class CheckinCode:
    qr_payload: str       # chuoi nhung trong anh QR
    digits: str           # ma 6 chu so tuong duong, de go tay
    rotate_seconds: int
    expires_in_seconds: int   # con bao lau thi doi ma


def _qr_content(session_id: int, code: str) -> str:
    """Noi dung anh QR. Co dia chi cong khai thi nhung thanh duong link: quet bang camera
    thuong cua dien thoai cung vao thang trang tu diem danh cua dung buoi, kem san ma. Chua
    cau hinh (chay tren may) thi giu chuoi ma, chi quet duoc tu trong ung dung."""
    base = settings.APP_PUBLIC_URL.rstrip("/")
    return f"{base}/#/self-checkin/{session_id}?code={code}" if base else code


def current_code(session_id: int) -> CheckinCode:
    now = time.time()
    window = _window(now)
    rotate = settings.CHECKIN_QR_ROTATE_SECONDS
    return CheckinCode(
        qr_payload=_qr_content(session_id, f"{QR_PREFIX}:{session_id}:{window}:{_signature(session_id, window)}"),
        digits=_digits(session_id, window),
        rotate_seconds=rotate,
        # Lam tron len: giay cuoi cua chu ky la con 1 giay, khong phai 0.
        expires_in_seconds=math.ceil((window + 1) * rotate - now),
    )


def verify(session_id: int, submitted: str | None) -> bool:
    """Chap nhan chuoi ma, ca duong link trong anh QR (may quet trong ung dung tra ve nguyen
    link) lan ma 6 chu so, trong o thoi gian hien tai hoac o lien truoc."""
    if not submitted:
        return False
    value = submitted.strip().rsplit("code=", 1)[-1]
    if not value:
        return False

    # So sanh dang bytes: compare_digest bao loi neu chuoi nguoi dung gui co ky tu ngoai ASCII.
    candidate = value.encode()
    window = _window()
    for w in (window, window - 1):
        if hmac.compare_digest(f"{QR_PREFIX}:{session_id}:{w}:{_signature(session_id, w)}".encode(), candidate):
            return True
        if hmac.compare_digest(_digits(session_id, w).encode(), candidate):
            return True
    return False
