from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app import schemas
from app.core.authz import STUDENT_MANAGERS, can_view_student
from app.core.config import settings
from app.core.media import delete_media
from app.core.security import get_current_user, require_roles
from app.db import models
from app.db.database import get_db
from app.db.models import ROLE_LECTURER, ROLE_STUDENT
from app.services import face_service

router = APIRouter(prefix="/faces", tags=["faces"])


def _my_student(db: Session, user: models.User) -> models.Student:
    student = db.query(models.Student).filter_by(user_id=user.id).first()
    if not student:
        raise HTTPException(404, "Khong tim thay ho so sinh vien")
    return student


@router.post("/enroll/{student_id}", response_model=schemas.EnrollResult)
async def enroll(
    student_id: int,
    images: list[UploadFile] = File(..., description="1 hoac nhieu anh khuon mat"),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """Dang ky khuon mat: nhan 1+ anh, moi anh -> 1 embedding trang thai "pending".
    Duoc thuc hien boi: chinh SV, admin/P.CTSV, hoac giang vien voi SV lop minh day.
    ok=True khi TAT CA anh trong lan goi nay dat."""
    student = db.get(models.Student, student_id)
    if not student:
        raise HTTPException(404, "Sinh vien khong ton tai")
    is_self = user.role == ROLE_STUDENT and student.user_id == user.id
    is_manager = user.role in STUDENT_MANAGERS
    is_own_lecturer = user.role == ROLE_LECTURER and can_view_student(user, student, db)
    if not (is_self or is_manager or is_own_lecturer):
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


@router.get("/mine", response_model=list[schemas.FaceMineOut])
def my_faces(
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles(ROLE_STUDENT)),
):
    """SV xem trang thai cac anh khuon mat da dang ky (kem ly do neu bi tu choi)."""
    student = _my_student(db, user)
    return (
        db.query(models.FaceEmbedding)
        .filter_by(student_id=student.id)
        .order_by(models.FaceEmbedding.created_at.desc())
        .all()
    )


@router.delete("/mine")
def delete_my_faces(
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles(ROLE_STUDENT)),
):
    """SV tu xoa TOAN BO du lieu khuon mat cua minh va rut lai dong y thu thap - sau do
    khong diem danh bang khuon mat duoc nua cho toi khi dong y + dang ky lai."""
    student = _my_student(db, user)
    embeddings = db.query(models.FaceEmbedding).filter_by(student_id=student.id).all()
    for emb in embeddings:
        delete_media(emb.source_image)
        db.delete(emb)
    student.consent_given = False
    student.consent_given_at = None
    db.commit()
    return {"ok": True, "deleted": len(embeddings)}


@router.get("/pending", response_model=list[schemas.FacePendingOut])
def list_pending(
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_roles(*STUDENT_MANAGERS)),
):
    """Danh sach embedding cho duyet, kem anh doi chieu va canh bao trung voi SV khac
    (neu co) - so sanh cosine chi voi embedding da duoc duyet."""
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


def _decide(db: Session, embedding_id: int) -> models.FaceEmbedding:
    emb = db.get(models.FaceEmbedding, embedding_id)
    if not emb:
        raise HTTPException(404, "Khong tim thay embedding")
    return emb


def _discard_review_image(emb: models.FaceEmbedding) -> None:
    """Anh doi chieu chi phuc vu viec duyet - xoa ngay khi da co quyet dinh."""
    delete_media(emb.source_image)
    emb.source_image = ""


@router.patch("/{embedding_id}/approve")
def approve_face(
    embedding_id: int,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_roles(*STUDENT_MANAGERS)),
):
    emb = _decide(db, embedding_id)
    emb.status = "approved"
    emb.reject_reason = ""
    _discard_review_image(emb)
    db.commit()
    return {"ok": True}


@router.patch("/{embedding_id}/reject")
def reject_face(
    embedding_id: int,
    body: schemas.FaceRejectBody,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_roles(*STUDENT_MANAGERS)),
):
    emb = _decide(db, embedding_id)
    if not body.reason.strip():
        raise HTTPException(400, "Can nhap ly do tu choi")
    emb.status = "rejected"
    emb.reject_reason = body.reason.strip()
    _discard_review_image(emb)
    db.commit()
    return {"ok": True}
