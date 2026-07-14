from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app import schemas
from app.core.config import settings
from app.core.security import get_current_user, require_roles
from app.db import models
from app.db.database import get_db
from app.services import face_service

router = APIRouter(prefix="/faces", tags=["faces"])


@router.post("/enroll/{student_id}", response_model=schemas.EnrollResult)
async def enroll(
    student_id: int,
    images: list[UploadFile] = File(..., description="1 hoac nhieu anh khuon mat"),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """Dang ky khuon mat: nhan 1+ anh, moi anh -> 1 embedding trang thai "pending".
    FE (trang /enroll) goi rieng tung buoi voi 1 anh/lan de bao loi ngay tai buoi
    do; ok=True khi TAT CA anh trong lan goi nay dat (khong con nguong 3 anh/lan
    nhu truoc - viec can du 3 buoi la do FE dieu phoi qua stepper)."""
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

    all_ok = ok_count == len(images) and ok_count > 0
    return schemas.EnrollResult(
        ok=all_ok,
        message="; ".join(messages),
        num_embeddings=ok_count,
    )


@router.get("/pending", response_model=list[schemas.FacePendingOut],
            dependencies=[Depends(require_roles("admin"))])
def list_pending(db: Session = Depends(get_db)):
    """Danh sach embedding cho duyet, kem canh bao trung voi SV khac (neu co) de
    admin thay ngay khi duyet - so sanh cosine chi voi embedding da duoc duyet."""
    pending = (
        db.query(models.FaceEmbedding)
        .filter(models.FaceEmbedding.status == "pending")
        .order_by(models.FaceEmbedding.created_at)
        .all()
    )

    result = []
    for emb in pending:
        distance = models.FaceEmbedding.embedding.cosine_distance(list(emb.embedding))
        nearest = (
            db.query(models.FaceEmbedding.student_id, distance.label("distance"))
            .filter(models.FaceEmbedding.student_id != emb.student_id,
                    models.FaceEmbedding.status == "approved")
            .order_by(distance)
            .first()
        )

        duplicate_warning = False
        dup_code = dup_sim = None
        if nearest is not None:
            other_student_id, dist = nearest
            similarity = round(1 - dist, 3)
            if similarity > settings.DUPLICATE_THRESHOLD:
                duplicate_warning = True
                dup_sim = similarity
                other_student = db.get(models.Student, other_student_id)
                dup_code = other_student.student_code if other_student else None

        result.append(schemas.FacePendingOut(
            id=emb.id, student_id=emb.student_id,
            student_code=emb.student.student_code, full_name=emb.student.user.full_name,
            source_image=emb.source_image, created_at=emb.created_at,
            duplicate_warning=duplicate_warning,
            duplicate_student_code=dup_code, duplicate_similarity=dup_sim,
        ))
    return result


@router.patch("/{embedding_id}/approve", dependencies=[Depends(require_roles("admin"))])
def approve_face(embedding_id: int, db: Session = Depends(get_db)):
    emb = db.get(models.FaceEmbedding, embedding_id)
    if not emb:
        raise HTTPException(404, "Khong tim thay embedding")
    emb.status = "approved"
    db.commit()
    return {"ok": True}


@router.patch("/{embedding_id}/reject", dependencies=[Depends(require_roles("admin"))])
def reject_face(embedding_id: int, body: schemas.FaceRejectBody, db: Session = Depends(get_db)):
    emb = db.get(models.FaceEmbedding, embedding_id)
    if not emb:
        raise HTTPException(404, "Khong tim thay embedding")
    if not body.reason.strip():
        raise HTTPException(400, "Can nhap ly do tu choi")
    emb.status = "rejected"
    emb.reject_reason = body.reason.strip()
    db.commit()
    return {"ok": True}
