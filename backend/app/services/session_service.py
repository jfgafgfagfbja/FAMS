"""Vong doi phien diem danh: han nhan diem danh, dong phien (sinh vang), tu dong dong
phien bi quen."""
import asyncio
import logging
from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import models
from app.db.database import SessionLocal
from app.services.attendance_stats import compute_class_attendance_stats

logger = logging.getLogger(__name__)

AUTO_CLOSE_INTERVAL_SECONDS = 60

# Dem so frame da nhan dien duoc 1 SV trong 1 phien, truoc khi ghi attendance record
# (multi-frame confirmation - giam nhan nham). Luu in-memory theo session_id, KHONG
# ben vung: mat het khi restart server (chap nhan duoc vi chi anh huong phien dang
# mo tai thoi diem restart, SV se phai duoc nhan dien lai tu dau). Don khi dong phien.
_confirm_counts: dict[int, dict[int, int]] = {}


def checkin_deadline(session: models.AttendanceSession) -> datetime:
    """Sau thoi diem nay (gio ket thuc tiet + SESSION_GRACE_MINUTES) khong nhan diem danh."""
    end = datetime.combine(session.session_date, session.schedule.end_time)
    return end + timedelta(minutes=settings.SESSION_GRACE_MINUTES)


def ensure_accepting_checkins(session: models.AttendanceSession) -> None:
    if session.status != "open":
        raise HTTPException(404, "Phien khong ton tai hoac da dong")
    if datetime.now() > checkin_deadline(session):
        raise HTTPException(400, "Da het gio nhan diem danh cho phien nay")


def close_session(db: Session, session: models.AttendanceSession) -> dict:
    """Dong phien: SV ghi danh chua co record -> absent. Tra kem danh sach SV vua vuot
    nguong canh bao chuyen can do phien nay (so voi truoc khi dong)."""
    class_id = session.schedule.class_id

    # Chup lai trang thai canh bao TRUOC khi dong phien, de sau do biet SV nao
    # "vua" vuot nguong (co the vi bi diem danh vang hoac chi vi tong so buoi tang len).
    warned_before = {
        r["student_id"] for r in compute_class_attendance_stats(db, class_id) if r["warning"]
    }

    checked_ids = {r.student_id for r in session.records}
    enrolled_ids = [
        student_id for (student_id,) in
        db.query(models.Enrollment.student_id).filter_by(class_id=class_id).all()
    ]
    absent_count = 0
    for student_id in enrolled_ids:
        if student_id not in checked_ids:
            db.add(models.AttendanceRecord(
                session_id=session.id, student_id=student_id, status="absent"))
            absent_count += 1

    session.status = "closed"
    session.closed_at = datetime.now()
    db.commit()
    _confirm_counts.pop(session.id, None)

    newly_warned = [
        r for r in compute_class_attendance_stats(db, class_id)
        if r["warning"] and r["student_id"] not in warned_before
    ]
    return {"ok": True, "absent": absent_count,
            "present": len(checked_ids), "newly_warned": newly_warned}


def auto_close_expired_sessions(db: Session, now: datetime | None = None) -> int:
    """Dong cac phien van mo sau han nhan diem danh (GV quen bam Dong phien)."""
    now = now or datetime.now()
    open_sessions = (
        db.query(models.AttendanceSession)
        .filter(models.AttendanceSession.status == "open")
        .all()
    )
    closed = 0
    for session in open_sessions:
        if now > checkin_deadline(session):
            close_session(db, session)
            closed += 1
            logger.info("Tu dong dong phien diem danh id=%s (qua han %s)",
                        session.id, checkin_deadline(session))
    return closed


async def run_auto_close_loop() -> None:
    while True:
        db = SessionLocal()
        try:
            auto_close_expired_sessions(db)
        except Exception:
            logger.exception("Loi khi tu dong dong phien diem danh")
        finally:
            db.close()
        await asyncio.sleep(AUTO_CLOSE_INTERVAL_SECONDS)
