import os

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.core.media import MEDIA_PREFIX, media_file_path, verify_media_signature

router = APIRouter(tags=["media"])


@router.get("/evidence/{file_path:path}")
def get_media(file_path: str, exp: int = 0, sig: str = ""):
    """Tra anh bang chung/anh dang ky khuon mat khi URL co chu ky hop le va con han.
    Chu ky chi duoc cap trong response cua cac endpoint da kiem tra quyen."""
    if not verify_media_signature(f"{MEDIA_PREFIX}{file_path}", exp, sig):
        raise HTTPException(403, "Lien ket anh khong hop le hoac da het han")
    full_path = media_file_path(file_path)
    if not full_path or not os.path.isfile(full_path):
        raise HTTPException(404, "Khong tim thay anh")
    return FileResponse(full_path, media_type="image/jpeg",
                        headers={"Cache-Control": "private, max-age=3000"})
