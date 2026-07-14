from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app import schemas
from app.core.security import get_current_user
from app.db import models
from app.db.database import get_db
from app.services import face_service

router = APIRouter(prefix="/faces", tags=["faces"])


@router.post("/enroll/{student_id}", response_model=schemas.EnrollResult)
async def enroll(
    student_id: int,
    images: list[UploadFile] = File(..., description="3-5 anh khuon mat"),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """Dang ky khuon mat: nhan 3-5 anh, moi anh -> 1 embedding."""
    student = db.get(models.Student, student_id)
    if not student:
        raise HTTPException(404, "Sinh vien khong ton tai")
    is_self = user.role == "student" and student.user_id == user.id
    if not is_self and user.role not in ("admin", "lecturer"):
        raise HTTPException(403, "Khong co quyen dang ky khuon mat cho sinh vien nay")
    if not student.consent_given:
        raise HTTPException(
            400, "Sinh vien chua xac nhan dong y thu thap du lieu khuon mat "
                 "(goi POST /students/{id}/consent truoc)")

    ok_count, messages = 0, []
    for img in images:
        data = await img.read()
        try:
            ok, msg = face_service.enroll_face(db, student_id, data)
        except ValueError as e:
            ok, msg = False, str(e)
        if ok:
            ok_count += 1
        messages.append(f"{img.filename}: {msg}")

    return schemas.EnrollResult(
        ok=ok_count >= 3,
        message="; ".join(messages)
        + ("" if ok_count >= 3 else f" — Can it nhat 3 anh dat, hien co {ok_count}"),
        num_embeddings=ok_count,
    )
