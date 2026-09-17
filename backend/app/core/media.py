"""URL co chu ky cho anh bang chung / anh dang ky khuon mat.

DB luu duong dan tho "/evidence/<...>". Khi tra ve client, duong dan duoc ky HMAC kem han
dung (?exp=&sig=) - chi nguoi da qua kiem tra quyen o endpoint tra du lieu moi nhan duoc URL
hop le. Cach nay dung duoc ca voi <img src> tren web (khong gui duoc header Authorization)
lan Image.network tren Flutter, thay cho StaticFiles cong khai truoc day.
"""
import hashlib
import hmac
import math
import os
import time
from typing import Annotated

from pydantic import PlainSerializer

from app.core.config import settings

MEDIA_PREFIX = "/evidence/"
# Lam tron han dung theo khoi 5 phut de URL on dinh trong 1 khoang -> client cache duoc anh.
_EXPIRY_BUCKET_SECONDS = 300


def _signature(path: str, exp: int) -> str:
    message = f"{path}|{exp}".encode()
    return hmac.new(settings.SECRET_KEY.encode(), message, hashlib.sha256).hexdigest()[:32]


def sign_media_path(path: str | None) -> str | None:
    if not path or "?" in path or not path.startswith(MEDIA_PREFIX):
        return path
    raw_exp = time.time() + settings.MEDIA_URL_EXPIRE_MINUTES * 60
    exp = int(math.ceil(raw_exp / _EXPIRY_BUCKET_SECONDS) * _EXPIRY_BUCKET_SECONDS)
    return f"{path}?exp={exp}&sig={_signature(path, exp)}"


def verify_media_signature(path: str, exp: int, sig: str) -> bool:
    if exp < time.time():
        return False
    return hmac.compare_digest(_signature(path, exp), sig)


def media_file_path(relative: str) -> str | None:
    """'<session_id>/<file>.jpg' -> duong dan that trong EVIDENCE_DIR, None neu co gang
    thoat ra ngoai thu muc (../)."""
    base = os.path.realpath(settings.EVIDENCE_DIR)
    full = os.path.realpath(os.path.join(base, relative))
    if not full.startswith(base + os.sep):
        return None
    return full


def delete_media(path: str | None) -> None:
    """Xoa file ung voi duong dan tho "/evidence/..." (bo qua neu khong ton tai)."""
    if not path or not path.startswith(MEDIA_PREFIX):
        return
    full = media_file_path(path[len(MEDIA_PREFIX):])
    if full and os.path.isfile(full):
        os.remove(full)


SignedMediaUrl = Annotated[
    str | None, PlainSerializer(sign_media_path, return_type=str | None, when_used="json")
]
