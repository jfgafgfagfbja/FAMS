import os
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app import schemas
from app.api.reports import compute_class_attendance_stats
from app.core.authz import ensure_class_access
from app.core.config import settings
from app.core.security import require_roles
from app.db import models
from app.db.database import get_db
from app.services import face_service

router = APIRouter(prefix="/sessions", tags=["attendance"])

# Dem so frame da nhan dien duoc 1 SV trong 1 phien, truoc khi ghi attendance record
# (multi-frame confirmation - giam nhan nham). Luu in-memory theo session_id, KHONG
# ben vung: mat het khi restart server (chap nhan duoc vi chi anh huong phien dang
# mo tai thoi diem restart, SV se phai duoc nhan dien lai tu dau). Don khi dong phien.
_confirm_counts: dict[int, dict[int, int]] = {}


def _save_evidence(image_bytes: bytes, session_id: int) -> str:
    """Luu frame lam bang chung, tra ve duong dan tuong doi (de dung voi /evidence/...)."""
    dir_path = os.path.join(settings.EVIDENCE_DIR, str(session_id))
    os.makedirs(dir_path, exist_ok=True)
    filename = f"{datetime.now():%Y%m%d%H%M%S}_{uuid.uuid4().hex[:6]}.jpg"
    with open(os.path.join(dir_path, filename), "wb") as f:
        f.write(image_bytes)
    return f"/evidence/{session_id}/{filename}"


def _get_session_or_404(db: Session, session_id: int) -> models.AttendanceSession:
    session = db.get(models.AttendanceSession, session_id)
    if not session:
        raise HTTPException(404, "Phien khong ton tai")
    return session


@router.post("", response_model=schemas.SessionOut)
def open_session(
    body: schemas.SessionCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles("lecturer", "admin")),
):
    schedule = db.get(models.Schedule, body.schedule_id)
    if not schedule:
        raise HTTPException(404, "Lich hoc khong ton tai")
    ensure_class_access(user, schedule.class_id, db)

    session = models.AttendanceSession(
        schedule_id=body.schedule_id, session_date=body.session_date
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get("/{session_id}", response_model=schemas.SessionDetail)
def get_session(
    session_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles("lecturer", "admin")),
):
    """Chi tiet 1 phien, kem thong tin lop/lich - frontend dung de lay class_id."""
    session = _get_session_or_404(db, session_id)
    ensure_class_access(user, session.schedule.class_id, db)

    clazz = session.schedule.clazz
    return schemas.SessionDetail(
        id=session.id, schedule_id=session.schedule_id,
        session_date=session.session_date, status=session.status,
        class_id=clazz.id, class_code=clazz.class_code, subject_name=clazz.subject_name,
        room=session.schedule.room, start_time=session.schedule.start_time,
        end_time=session.schedule.end_time,
    )


@router.post("/{session_id}/recognize",
             response_model=list[schemas.RecognizeResult])
async def recognize(
    session_id: int,
    frame: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles("lecturer", "admin")),
):
    """Nhan 1 frame tu webcam, nhan dien va tu dong ghi diem danh."""
    session = _get_session_or_404(db, session_id)
    if session.status != "open":
        raise HTTPException(404, "Phien khong ton tai hoac da dong")
    ensure_class_access(user, session.schedule.class_id, db)

    class_id = session.schedule.class_id
    data = await frame.read()
    matches = face_service.recognize_frame(db, data, class_id)

    evidence_path = None
    results = []
    for m in matches:
        is_spoof = m.get("is_spoof", False)
        liveness_score = m.get("liveness_score")
        student = db.get(models.Student, m["student_id"]) if m["student_id"] else None

        if is_spoof:
            # Nghi gia mao: van luu anh bang chung de admin xem lai ai gian lan,
            # nhung khong ghi attendance record du co nhan ra danh tinh hay khong.
            if evidence_path is None:
                evidence_path = _save_evidence(data, session_id)
            results.append(schemas.RecognizeResult(
                student_id=student.id if student else None,
                student_code=student.student_code if student else None,
                full_name=student.user.full_name if student else None,
                confidence=m["confidence"], status="spoof",
                evidence_image=evidence_path, liveness_score=liveness_score,
                bbox=m.get("bbox")))
            continue

        if student is None:
            results.append(schemas.RecognizeResult(
                student_id=None, student_code=None, full_name=None,
                confidence=m["confidence"], status="unknown", evidence_image=None,
                liveness_score=liveness_score, bbox=m.get("bbox")))
            continue

        existed = (
            db.query(models.AttendanceRecord)
            .filter_by(session_id=session_id, student_id=student.id)
            .first()
        )
        confirm_count = confirm_needed = None
        if existed:
            status = "already_checked"
            evidence = existed.evidence_image
        else:
            # Chi ghi record khi da nhan dien du CONFIRM_FRAMES lan trong phien nay
            # (khong can lien tiep) - giam nhan nham do 1 frame loi thoang qua.
            session_counts = _confirm_counts.setdefault(session_id, {})
            session_counts[student.id] = session_counts.get(student.id, 0) + 1
            confirm_count = session_counts[student.id]
            confirm_needed = settings.CONFIRM_FRAMES

            if confirm_count < confirm_needed:
                results.append(schemas.RecognizeResult(
                    student_id=student.id, student_code=student.student_code,
                    full_name=student.user.full_name,
                    confidence=m["confidence"], status="confirming",
                    evidence_image=None, liveness_score=liveness_score,
                    bbox=m.get("bbox"), confirm_count=confirm_count,
                    confirm_needed=confirm_needed))
                continue

            # Dung gio hay muon: so voi gio bat dau tiet + LATE_AFTER_MINUTES
            start = datetime.combine(session.session_date,
                                     session.schedule.start_time)
            late = datetime.now() > start + timedelta(
                minutes=settings.LATE_AFTER_MINUTES)
            if evidence_path is None:
                evidence_path = _save_evidence(data, session_id)
            db.add(models.AttendanceRecord(
                session_id=session_id, student_id=student.id,
                status="late" if late else "present",
                confidence=m["confidence"], evidence_image=evidence_path))
            db.commit()
            status = "recognized"
            evidence = evidence_path

        results.append(schemas.RecognizeResult(
            student_id=student.id, student_code=student.student_code,
            full_name=student.user.full_name,
            confidence=m["confidence"], status=status,
            evidence_image=evidence or None, liveness_score=liveness_score,
            bbox=m.get("bbox"), confirm_count=confirm_count, confirm_needed=confirm_needed))
    return results


@router.post("/{session_id}/manual", response_model=schemas.RecordOut)
def manual_check(
    session_id: int,
    body: schemas.ManualCheck,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles("lecturer", "admin")),
):
    """Giang vien xac nhan tay khi SV khong nhan dien duoc."""
    session = _get_session_or_404(db, session_id)
    ensure_class_access(user, session.schedule.class_id, db)

    # Chan trung truoc khi insert - UniqueConstraint(session_id, student_id) o DB
    # se chan o tang du lieu, nhung khong bat truoc thi se lo ra IntegrityError 500
    # thay vi 1 loi 400 de hieu.
    existed = (
        db.query(models.AttendanceRecord)
        .filter_by(session_id=session_id, student_id=body.student_id)
        .first()
    )
    if existed:
        raise HTTPException(400, "Sinh vien nay da co record trong phien nay")

    record = models.AttendanceRecord(
        session_id=session_id, student_id=body.student_id, status="manual")
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.patch("/{session_id}/close")
def close_session(
    session_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles("lecturer", "admin")),
):
    """Dong phien: SV chua co record -> absent. Tra kem danh sach SV vua vuot
    nguong canh bao chuyen can do phien nay (so voi truoc khi dong)."""
    session = _get_session_or_404(db, session_id)
    ensure_class_access(user, session.schedule.class_id, db)
    class_id = session.schedule.class_id

    # Chup lai trang thai canh bao TRUOC khi dong phien, de sau do biet SV nao
    # "vua" vuot nguong (co the vi bi diem danh vang hoac chi vi tong so buoi tang len).
    warned_before = {
        r["student_id"] for r in compute_class_attendance_stats(db, class_id) if r["warning"]
    }

    checked_ids = {r.student_id for r in session.records}
    enrolled = (
        db.query(models.Enrollment)
        .filter_by(class_id=class_id)
        .all()
    )
    absent_count = 0
    for e in enrolled:
        if e.student_id not in checked_ids:
            db.add(models.AttendanceRecord(
                session_id=session_id, student_id=e.student_id, status="absent"))
            absent_count += 1

    session.status = "closed"
    session.closed_at = datetime.now()
    db.commit()
    _confirm_counts.pop(session_id, None)

    newly_warned = [
        r for r in compute_class_attendance_stats(db, class_id)
        if r["warning"] and r["student_id"] not in warned_before
    ]
    return {"ok": True, "absent": absent_count,
            "present": len(checked_ids), "newly_warned": newly_warned}


@router.get("/{session_id}/records", response_model=list[schemas.RecordOut])
def list_records(
    session_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles("lecturer", "admin")),
):
    session = _get_session_or_404(db, session_id)
    ensure_class_access(user, session.schedule.class_id, db)
    return (db.query(models.AttendanceRecord)
            .filter_by(session_id=session_id).all())


ALLOWED_EDIT_STATUSES = ("present", "late", "absent", "excused")


@router.patch("/{session_id}/records/{record_id}", response_model=schemas.RecordOut)
def update_record(
    session_id: int,
    record_id: int,
    body: schemas.RecordUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles("lecturer", "admin")),
):
    """Sua trang thai 1 record (vd SV nop don phep sau buoi hoc). Van sua duoc ke ca
    khi phien da dong, nhung bat buoc phai co ly do - moi lan sua deu luu vao
    AttendanceAudit de sau nay xem lai lich su."""
    session = _get_session_or_404(db, session_id)
    ensure_class_access(user, session.schedule.class_id, db)

    record = db.get(models.AttendanceRecord, record_id)
    if not record or record.session_id != session_id:
        raise HTTPException(404, "Record khong ton tai trong phien nay")

    if body.status not in ALLOWED_EDIT_STATUSES:
        raise HTTPException(400, "Trang thai khong hop le")
    if not body.reason.strip():
        raise HTTPException(400, "Can nhap ly do khi sua diem danh")

    old_status = record.status
    record.status = body.status
    db.add(models.AttendanceAudit(
        record_id=record.id, changed_by=user.id,
        old_status=old_status, new_status=body.status, reason=body.reason.strip(),
    ))
    db.commit()
    db.refresh(record)
    return record


@router.get("/{session_id}/records/{record_id}/audits",
            response_model=list[schemas.AttendanceAuditOut])
def list_record_audits(
    session_id: int,
    record_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles("lecturer", "admin")),
):
    """Xem lich su sua diem danh cua 1 record."""
    session = _get_session_or_404(db, session_id)
    ensure_class_access(user, session.schedule.class_id, db)

    record = db.get(models.AttendanceRecord, record_id)
    if not record or record.session_id != session_id:
        raise HTTPException(404, "Record khong ton tai trong phien nay")

    return (
        db.query(models.AttendanceAudit)
        .filter_by(record_id=record_id)
        .order_by(models.AttendanceAudit.changed_at.desc())
        .all()
    )
