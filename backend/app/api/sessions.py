import os
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import schemas
from app.core.authz import (CLASS_VIEWERS, can_excuse_record, ensure_class_access,
                            ensure_class_view, filter_classes)
from app.core.config import settings
from app.core.security import require_roles
from app.db import models
from app.db.database import get_db
from app.db.models import (ROLE_ADMIN, ROLE_AFFAIRS, ROLE_FACULTY, ROLE_LECTURER, ROLE_STUDENT)
from app.services import face_service
from app.services.session_service import (_confirm_counts, checkin_deadline,
                                          close_session as close_session_records,
                                          ensure_accepting_checkins)

router = APIRouter(prefix="/sessions", tags=["attendance"])

__all__ = ["router", "_confirm_counts"]


def _save_evidence(image_bytes: bytes, session_id: int) -> str:
    """Luu frame lam bang chung, tra ve duong dan tho (API ky URL khi tra ve client)."""
    dir_path = os.path.join(settings.EVIDENCE_DIR, str(session_id))
    os.makedirs(dir_path, exist_ok=True)
    filename = f"{datetime.now():%Y%m%d%H%M%S}_{uuid.uuid4().hex[:12]}.jpg"
    with open(os.path.join(dir_path, filename), "wb") as f:
        f.write(image_bytes)
    return f"/evidence/{session_id}/{filename}"


def _get_session_or_404(db: Session, session_id: int) -> models.AttendanceSession:
    session = db.get(models.AttendanceSession, session_id)
    if not session:
        raise HTTPException(404, "Phien khong ton tai")
    return session


def _session_detail(session: models.AttendanceSession) -> schemas.SessionDetail:
    clazz = session.schedule.clazz
    return schemas.SessionDetail(
        id=session.id, schedule_id=session.schedule_id,
        session_date=session.session_date, status=session.status,
        opened_at=session.opened_at, closed_at=session.closed_at,
        class_id=clazz.id, class_code=clazz.class_code, subject_name=clazz.subject_name,
        room=session.schedule.room, start_time=session.schedule.start_time,
        end_time=session.schedule.end_time,
        lecturer_name=clazz.lecturer.user.full_name if clazz.lecturer else None,
        checkin_deadline=checkin_deadline(session),
    )


def _is_late(session: models.AttendanceSession) -> bool:
    """Dung gio hay muon: so voi gio bat dau tiet + LATE_AFTER_MINUTES."""
    start = datetime.combine(session.session_date, session.schedule.start_time)
    return datetime.now() > start + timedelta(minutes=settings.LATE_AFTER_MINUTES)


@router.post("", response_model=schemas.SessionOut)
def open_session(
    body: schemas.SessionCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles(ROLE_LECTURER, ROLE_ADMIN)),
):
    """Mo phien diem danh. Chi cho mo khi: dung ngay hom nay, dung thu cua lich hoc,
    trong khung [start_time - EARLY_OPEN_MINUTES, end_time] va chua co phien nao cua
    cung lich hoc trong ngay (moi rang buoc sai tra 400 voi message rieng)."""
    schedule = db.get(models.Schedule, body.schedule_id)
    if not schedule:
        raise HTTPException(404, "Lich hoc khong ton tai")
    ensure_class_access(user, schedule.class_id, db)

    now = datetime.now()
    if body.session_date != now.date():
        raise HTTPException(400, "Chi duoc mo phien diem danh cho ngay hom nay")
    if body.session_date.weekday() != schedule.weekday:
        raise HTTPException(400, "Ngay diem danh khong dung thu cua lich hoc nay")

    open_from = datetime.combine(body.session_date, schedule.start_time) - timedelta(
        minutes=settings.EARLY_OPEN_MINUTES)
    if now < open_from:
        raise HTTPException(400, f"Chua den gio - chi mo duoc phien tu {open_from:%H:%M}")
    if now > datetime.combine(body.session_date, schedule.end_time):
        raise HTTPException(400, "Tiet hoc da ket thuc, khong the mo phien diem danh")

    existed = (
        db.query(models.AttendanceSession)
        .filter_by(schedule_id=body.schedule_id, session_date=body.session_date)
        .first()
    )
    if existed:
        raise HTTPException(400, "Da co phien diem danh cho lich hoc nay trong ngay hom nay")

    session = models.AttendanceSession(
        schedule_id=body.schedule_id, session_date=body.session_date
    )
    db.add(session)
    try:
        db.commit()
    except IntegrityError:
        # 2 request mo phien gan nhu dong thoi: kiem tra existed o tren deu chua thay
        # phien nao, UNIQUE(schedule_id, session_date) o DB chan request den sau.
        db.rollback()
        raise HTTPException(400, "Da co phien diem danh cho lich hoc nay trong ngay hom nay")
    db.refresh(session)
    return session


@router.get("", response_model=list[schemas.SessionDetail])
def list_sessions(
    status: str | None = None,
    class_id: int | None = None,
    mine: bool = False,
    limit: int | None = None,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles(*CLASS_VIEWERS)),
):
    """Danh sach phien diem danh trong pham vi xem lop cua user (GV: lop minh day,
    Khoa: lop Khoa quan ly), loc theo status (open/closed) va class_id. Tham so mine
    giu de tuong thich - pham vi da duoc gioi han theo vai tro."""
    query = filter_classes(
        db.query(models.AttendanceSession).join(models.Schedule).join(models.Class), user, db)
    if status:
        query = query.filter(models.AttendanceSession.status == status)
    if class_id is not None:
        query = query.filter(models.Class.id == class_id)

    query = query.order_by(models.AttendanceSession.session_date.desc(),
                           models.AttendanceSession.opened_at.desc())
    if limit is not None:
        query = query.limit(limit)
    return [_session_detail(s) for s in query.all()]


@router.get("/{session_id}", response_model=schemas.SessionDetail)
def get_session(
    session_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles(*CLASS_VIEWERS)),
):
    """Chi tiet 1 phien, kem thong tin lop/lich - frontend dung de lay class_id."""
    session = _get_session_or_404(db, session_id)
    ensure_class_view(user, session.schedule.class_id, db)
    return _session_detail(session)


@router.get("/{session_id}/roster", response_model=list[schemas.RosterEntryOut])
def session_roster(
    session_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles(*CLASS_VIEWERS)),
):
    """Danh sach SV cua lop gop voi trang thai diem danh cua phien nay trong 1 lan
    goi (thay vi FE phai goi rieng /classes/{id}/students + /sessions/{id}/records)."""
    session = _get_session_or_404(db, session_id)
    ensure_class_view(user, session.schedule.class_id, db)
    class_id = session.schedule.class_id

    students = (
        db.query(models.Student)
        .join(models.Enrollment, models.Enrollment.student_id == models.Student.id)
        .filter(models.Enrollment.class_id == class_id)
        .order_by(models.Student.student_code)
        .all()
    )
    records = {
        r.student_id: r
        for r in db.query(models.AttendanceRecord).filter_by(session_id=session_id).all()
    }

    result = []
    for s in students:
        r = records.get(s.id)
        result.append(schemas.RosterEntryOut(
            student_id=s.id, student_code=s.student_code, full_name=s.user.full_name,
            status=r.status if r else None,
            confidence=r.confidence if r else None,
            evidence_image=r.evidence_image if r else None,
            checked_at=r.checked_at if r else None,
            record_id=r.id if r else None,
            source=r.source if r else None,
            latitude=r.latitude if r else None,
            longitude=r.longitude if r else None,
            location_accuracy=r.location_accuracy if r else None,
        ))
    return result


@router.post("/{session_id}/recognize",
             response_model=list[schemas.RecognizeResult])
async def recognize(
    session_id: int,
    frame: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles(ROLE_LECTURER, ROLE_ADMIN)),
):
    """Nhan 1 frame tu camera lop hoc, nhan dien va tu dong ghi diem danh."""
    session = _get_session_or_404(db, session_id)
    ensure_class_access(user, session.schedule.class_id, db)
    ensure_accepting_checkins(session)

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
            # Nghi gia mao: van luu anh bang chung de can bo xem lai ai gian lan,
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

            if evidence_path is None:
                evidence_path = _save_evidence(data, session_id)
            db.add(models.AttendanceRecord(
                session_id=session_id, student_id=student.id,
                status="late" if _is_late(session) else "present",
                confidence=m["confidence"], evidence_image=evidence_path,
                source="camera"))
            try:
                db.commit()
                status = "recognized"
                evidence = evidence_path
            except IntegrityError:
                # Frame khac (vd 2 thiet bi cung quet) vua ghi record cho SV nay.
                db.rollback()
                status = "already_checked"
                evidence = None

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
    user: models.User = Depends(require_roles(ROLE_LECTURER, ROLE_ADMIN)),
):
    """Giang vien xac nhan tay khi SV khong nhan dien duoc (chi trong phien dang mo,
    chi SV ghi danh lop). Sau khi dong phien, sua trang thai qua PATCH records."""
    session = _get_session_or_404(db, session_id)
    ensure_class_access(user, session.schedule.class_id, db)
    if session.status != "open":
        raise HTTPException(400, "Phien da dong, hay sua trang thai diem danh thay vi xac nhan tay")

    enrolled = (
        db.query(models.Enrollment)
        .filter_by(class_id=session.schedule.class_id, student_id=body.student_id)
        .first()
    )
    if not enrolled:
        raise HTTPException(400, "Sinh vien khong thuoc lop hoc phan nay")

    existed = (
        db.query(models.AttendanceRecord)
        .filter_by(session_id=session_id, student_id=body.student_id)
        .first()
    )
    if existed:
        raise HTTPException(400, "Sinh vien nay da co record trong phien nay")

    record = models.AttendanceRecord(
        session_id=session_id, student_id=body.student_id, status="manual",
        source="manual")
    db.add(record)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(400, "Sinh vien nay da co record trong phien nay")
    db.refresh(record)
    return record


@router.post("/{session_id}/self-checkin", response_model=schemas.SelfCheckinResult)
async def self_checkin(
    session_id: int,
    frame: UploadFile = File(...),
    latitude: float | None = Form(None),
    longitude: float | None = Form(None),
    accuracy: float | None = Form(None),
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles(ROLE_STUDENT)),
):
    """SV tu chup selfie de diem danh (khac luong GV quet camera ca lop o
    /recognize): chi nhan dien so voi khuon mat cua CHINH SV dang dang nhap
    (recognize_self), kem toa do GPS (neu SV cho phep) de lam bang chung thoi gian +
    dia diem diem danh. Chi nhan truoc han checkin_deadline cua phien."""
    session = _get_session_or_404(db, session_id)
    ensure_accepting_checkins(session)

    student = db.query(models.Student).filter_by(user_id=user.id).first()
    if not student:
        raise HTTPException(404, "Khong tim thay ho so sinh vien")

    class_id = session.schedule.class_id
    enrolled = (
        db.query(models.Enrollment)
        .filter_by(class_id=class_id, student_id=student.id)
        .first()
    )
    if not enrolled:
        raise HTTPException(403, "Ban khong ghi danh lop hoc phan nay")

    existed = (
        db.query(models.AttendanceRecord)
        .filter_by(session_id=session_id, student_id=student.id)
        .first()
    )
    if existed:
        return schemas.SelfCheckinResult(
            status="already_checked", record_id=existed.id, record_status=existed.status,
            evidence_image=existed.evidence_image or None, confidence=existed.confidence,
            message="Ban da diem danh phien nay roi")

    data = await frame.read()
    result = face_service.recognize_self(db, data, student.id)

    if result["status"] == "no_face":
        return schemas.SelfCheckinResult(
            status="no_face", message="Khong tim thay khuon mat trong anh, hay thu lai")
    if result["status"] == "multiple_faces":
        return schemas.SelfCheckinResult(
            status="multiple_faces",
            message="Anh co nhieu hon 1 khuon mat, hay chup rieng minh ban de he thong xac dinh dung danh tinh")
    if result["status"] == "spoof":
        evidence_path = _save_evidence(data, session_id)
        return schemas.SelfCheckinResult(
            status="spoof", liveness_score=result["liveness_score"], evidence_image=evidence_path,
            message="Anh nghi la gia mao (anh in/anh chup lai man hinh), vui long chup truc tiep")
    if result["status"] == "not_matched":
        return schemas.SelfCheckinResult(
            status="not_matched", confidence=result["confidence"],
            liveness_score=result["liveness_score"],
            message="Khuon mat khong khop voi du lieu da dang ky cua ban. "
                    "Neu chua dang ky khuon mat, hay vao muc \"Dang ky khuon mat\" truoc.")

    evidence_path = _save_evidence(data, session_id)
    record = models.AttendanceRecord(
        session_id=session_id, student_id=student.id,
        status="late" if _is_late(session) else "present",
        confidence=result["confidence"], evidence_image=evidence_path,
        source="selfie", latitude=latitude, longitude=longitude, location_accuracy=accuracy,
    )
    db.add(record)
    try:
        db.commit()
    except IntegrityError:
        # 2 request tu diem danh gan nhu dong thoi (vd double-click): UNIQUE
        # (session_id, student_id) chan o DB, tra ve record da co thay vi loi 500.
        db.rollback()
        existed = (
            db.query(models.AttendanceRecord)
            .filter_by(session_id=session_id, student_id=student.id)
            .first()
        )
        return schemas.SelfCheckinResult(
            status="already_checked", record_id=existed.id if existed else None,
            record_status=existed.status if existed else None,
            message="Ban da diem danh phien nay roi")
    db.refresh(record)
    return schemas.SelfCheckinResult(
        status="recognized", confidence=result["confidence"],
        liveness_score=result["liveness_score"], evidence_image=evidence_path,
        record_id=record.id, record_status=record.status,
        message="Diem danh thanh cong",
    )


@router.patch("/{session_id}/close")
def close_session(
    session_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles(ROLE_LECTURER, ROLE_ADMIN)),
):
    """Dong phien: SV chua co record -> absent. Tra kem danh sach SV vua vuot
    nguong canh bao chuyen can do phien nay (so voi truoc khi dong)."""
    session = _get_session_or_404(db, session_id)
    ensure_class_access(user, session.schedule.class_id, db)
    if session.status != "open":
        raise HTTPException(400, "Phien diem danh da dong truoc do")
    return close_session_records(db, session)


@router.get("/{session_id}/records", response_model=list[schemas.RecordOut])
def list_records(
    session_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles(*CLASS_VIEWERS)),
):
    session = _get_session_or_404(db, session_id)
    ensure_class_view(user, session.schedule.class_id, db)
    return (db.query(models.AttendanceRecord)
            .filter_by(session_id=session_id).all())


ALLOWED_EDIT_STATUSES = ("present", "late", "absent", "excused")
EXCUSE_EDITORS = (ROLE_AFFAIRS, ROLE_FACULTY)


@router.patch("/{session_id}/records/{record_id}", response_model=schemas.RecordOut)
def update_record(
    session_id: int,
    record_id: int,
    body: schemas.RecordUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles(ROLE_LECTURER, ROLE_ADMIN, *EXCUSE_EDITORS)),
):
    """Sua trang thai 1 record (vd SV nop don phep sau buoi hoc). Van sua duoc ke ca
    khi phien da dong, nhung bat buoc phai co ly do - moi lan sua deu luu vao
    AttendanceAudit. GV lop/admin sua moi trang thai; P.CTSV va Khoa (trong pham vi)
    chi duyet "Co phep" (-> excused) hoac huy duyet (excused -> absent)."""
    session = _get_session_or_404(db, session_id)

    record = db.get(models.AttendanceRecord, record_id)
    if not record or record.session_id != session_id:
        raise HTTPException(404, "Record khong ton tai trong phien nay")

    if body.status not in ALLOWED_EDIT_STATUSES:
        raise HTTPException(400, "Trang thai khong hop le")
    if not body.reason.strip():
        raise HTTPException(400, "Can nhap ly do khi sua diem danh")

    if user.role in EXCUSE_EDITORS:
        if not can_excuse_record(user, record, db):
            raise HTTPException(403, "Khong co quyen voi sinh vien/lop hoc phan nay")
        is_excuse = body.status == "excused"
        is_revert = record.status == "excused" and body.status == "absent"
        if not (is_excuse or is_revert):
            raise HTTPException(
                403, "Phong ban chi duoc duyet 'Co phep' hoac huy duyet ve 'Vang'")
    else:
        ensure_class_access(user, session.schedule.class_id, db)

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
    user: models.User = Depends(require_roles(*CLASS_VIEWERS)),
):
    """Xem lich su sua diem danh cua 1 record."""
    session = _get_session_or_404(db, session_id)
    ensure_class_view(user, session.schedule.class_id, db)

    record = db.get(models.AttendanceRecord, record_id)
    if not record or record.session_id != session_id:
        raise HTTPException(404, "Record khong ton tai trong phien nay")

    return (
        db.query(models.AttendanceAudit)
        .filter_by(record_id=record_id)
        .order_by(models.AttendanceAudit.changed_at.desc())
        .all()
    )
