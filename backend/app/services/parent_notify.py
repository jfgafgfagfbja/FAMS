"""Bao cho phu huynh moi khi con duoc ghi nhan diem danh: co mat, di muon, vang, co phep.

Hai phan tach roi nhau:

1. SINH THONG BAO - bat su kien before_flush cua SQLAlchemy. Bat ky doan code nao tao ban
   ghi diem danh hoac doi trang thai cua no deu tu dong sinh thong bao, trong CUNG giao
   dich: GV quet camera ca lop, SV tu diem danh, GV xac nhan tay, dong phien ghi vang, GV
   sua trang thai. Ban ghi diem danh bi huy (vd hai may quet trung mot SV) thi thong bao
   cung bi huy theo. Them cach diem danh moi sau nay cung khong phai nho goi them ham nao.

2. GUI EMAIL - tac vu nen lay cac thong bao dang cho, gui qua SMTP, ghi lai ket qua. Tach
   rieng de Gmail cham hay mat mang khong lam cham hay hong viec diem danh; thu loi duoc
   gui lai toi NOTIFY_EMAIL_MAX_ATTEMPTS lan.
"""
import asyncio
import logging
from datetime import datetime

from sqlalchemy import event, inspect
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import models
from app.db.database import SessionLocal
from app.services import email_service

logger = logging.getLogger(__name__)

KIND_PRESENT = "attendance_present"
KIND_LATE = "attendance_late"
KIND_ABSENT = "attendance_absent"
KIND_EXCUSED = "attendance_excused"

# trang thai ban ghi -> (loai thong bao, cach noi trong cau)
_EVENTS = {
    "present": (KIND_PRESENT, "có mặt"),
    "manual": (KIND_PRESENT, "có mặt"),
    "late": (KIND_LATE, "đi muộn"),
    "absent": (KIND_ABSENT, "vắng"),
    "excused": (KIND_EXCUSED, "vắng có phép"),
}


# ------------------------------------------------------------------ sinh thong bao

@event.listens_for(Session, "before_flush")
def _notify_on_attendance_change(session: Session, _flush_context, _instances) -> None:
    changed: list[tuple[models.AttendanceRecord, bool]] = []
    for obj in session.new:
        if isinstance(obj, models.AttendanceRecord):
            changed.append((obj, False))
    for obj in session.dirty:
        if isinstance(obj, models.AttendanceRecord) and inspect(obj).attrs.status.history.has_changes():
            changed.append((obj, True))
    if not changed:
        return
    # Truy van ben trong before_flush ma de autoflush thi se goi lai chinh no.
    with session.no_autoflush:
        for record, is_update in changed:
            _queue_for_record(session, record, is_update)


def _queue_for_record(db: Session, record: models.AttendanceRecord, is_update: bool) -> None:
    event_info = _EVENTS.get(record.status)
    if event_info is None:
        return
    kind, label = event_info

    links = db.query(models.ParentStudent).filter_by(student_id=record.student_id).all()
    if not links:
        return
    student = db.get(models.Student, record.student_id)
    session = db.get(models.AttendanceSession, record.session_id)
    if student is None or session is None:
        return

    title, body = _compose(student, session, record, label, is_update)
    can_email = email_service.is_configured()
    for link in links:
        parent = link.parent
        if kind == KIND_PRESENT and not parent.notify_present:
            continue
        # Luong ghi chay lai (hoac doi qua doi lai cung mot trang thai) khong bao trung.
        if record.id is not None and db.query(models.Notification).filter_by(
                user_id=parent.user_id, record_id=record.id, kind=kind).first():
            continue
        wants_email = can_email and parent.notify_email and bool(parent.user.email)
        db.add(models.Notification(
            user_id=parent.user_id, kind=kind, title=title, body=body,
            link=f"/children/{student.id}", record=record,
            email_status="pending" if wants_email else "skipped",
        ))


def _compose(student: models.Student, session: models.AttendanceSession,
             record: models.AttendanceRecord, label: str, is_update: bool) -> tuple[str, str]:
    schedule = session.schedule
    clazz = schedule.clazz
    name = student.user.full_name
    room = schedule.classroom.name if schedule.classroom else (
        f"phòng {schedule.room}" if schedule.room else "")
    when = (f"ngày {session.session_date:%d/%m/%Y}, "
            f"{schedule.start_time:%H:%M}–{schedule.end_time:%H:%M}")
    lesson = f"buổi học {clazz.subject_name} ({clazz.class_code}) {when}" + (f", {room}" if room else "")

    title = f"{'Cập nhật: ' if is_update else ''}{name} {label} — {clazz.class_code}"
    if record.status == "absent":
        body = (f"{name} ({student.student_code}) vắng {lesson}. "
                "Buổi học đã kết thúc mà không có ghi nhận điểm danh.")
    elif record.status == "excused":
        body = f"Giảng viên ghi nhận {name} ({student.student_code}) vắng có phép {lesson}."
    else:
        # Ban ghi moi chua co checked_at (CSDL tu dien luc ghi) - dung gio hien tai.
        at = (record.checked_at or datetime.now()).strftime("%H:%M")
        body = f"{name} ({student.student_code}) được ghi nhận {label} lúc {at}, {lesson}."
    return title, body


# ------------------------------------------------------------------ gui email

def _email_text(notification: models.Notification) -> str:
    lines = [notification.body]
    if settings.APP_PUBLIC_URL and notification.link:
        lines += ["", f"Xem chi tiết: {settings.APP_PUBLIC_URL.rstrip('/')}/#{notification.link}"]
    lines += [
        "", "—",
        "Bạn nhận thư này vì là phụ huynh trên hệ thống điểm danh FAMS.",
        "Muốn tắt email hoặc chỉ nhận tin khi con đi muộn/vắng: vào Tài khoản → Thông báo.",
    ]
    return "\n".join(lines)


def send_pending_emails(db: Session | None = None, limit: int = 20) -> int:
    """Gui mot lo thu dang cho. Tra ve so thu gui thanh cong. Khong truyen db thi tu mo
    phien rieng (tac vu nen); test truyen phien cua minh vao."""
    if not email_service.is_configured():
        return 0
    own_session = db is None
    db = db or SessionLocal()
    try:
        # SKIP LOCKED: chay nhieu tien trinh thi moi thu chi mot tien trinh gui.
        rows = (
            db.query(models.Notification)
            .filter(models.Notification.email_status == "pending")
            .order_by(models.Notification.id)
            .limit(limit)
            .with_for_update(skip_locked=True)
            .all()
        )
        if not rows:
            return 0

        sent = 0
        try:
            with email_service.smtp_connection() as server:
                for n in rows:
                    try:
                        server.send_message(email_service.build_message(
                            n.user.email, f"[FAMS] {n.title}", _email_text(n)))
                        n.email_status = "sent"
                        n.emailed_at = datetime.now()
                        n.email_error = None
                        sent += 1
                    except Exception as exc:  # loi rieng mot thu, vd dia chi nhan sai
                        _mark_failure(n, exc)
        except Exception as exc:  # khong ket noi/dang nhap duoc SMTP - ca lo thu deu loi
            logger.warning("Khong ket noi duoc may chu email: %s", exc)
            for n in rows:
                if n.email_status == "pending":
                    _mark_failure(n, exc)
        db.commit()
        return sent
    finally:
        if own_session:
            db.close()


def _mark_failure(n: models.Notification, exc: Exception) -> None:
    n.email_attempts = (n.email_attempts or 0) + 1
    n.email_error = str(exc)[:255]
    if n.email_attempts >= settings.NOTIFY_EMAIL_MAX_ATTEMPTS:
        n.email_status = "failed"


async def run_notification_email_loop() -> None:
    while True:
        try:
            await asyncio.to_thread(send_pending_emails)
        except Exception:
            logger.exception("Loi khi gui email thong bao")
        await asyncio.sleep(settings.NOTIFY_EMAIL_INTERVAL_SECONDS)
