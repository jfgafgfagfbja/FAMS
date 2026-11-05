"""Nhat ky he thong (bang audit_logs).

Ghi TU DONG moi thay doi du lieu quan ly bang su kien after_flush cua SQLAlchemy: bat ky
endpoint nao them/sua/xoa SV, GV, lop, lich, phong, don vi, can bo, khuon mat, dong y sinh
trac hoc, phien, ket qua diem danh... deu de lai dau vet, khong phu thuoc nguoi viet
endpoint co nho goi ham ghi log hay khong. Chon after_flush vi luc do ban ghi moi da co
khoa chinh ma lich su thay doi cua tung cot van con.

Ai la nguoi thao tac: get_current_user (core/security.py) gan nguoi dung + IP vao
db.info["audit_actor"] - phien CSDL dung chung trong mot request nen moi thay doi trong
request do duoc gan dung nguoi. Thay doi khong qua request (tac vu nen tu dong dong phien)
ghi la he thong.

Dang nhap, dang xuat, xuat bao cao khong lam doi du lieu nao nen ghi tuong minh bang
record_event().
"""
import json
from datetime import date, datetime, time

from fastapi import Request
from sqlalchemy import event, inspect
from sqlalchemy.orm import Session

from app.db import models

# Loai doi tuong duoc theo doi -> ten ngan ghi vao target_type.
_TRACKED: dict[type, str] = {
    models.User: "user",
    models.Unit: "unit",
    models.Staff: "staff",
    models.Student: "student",
    models.Lecturer: "lecturer",
    models.Parent: "parent",
    models.ParentStudent: "parent_link",
    models.Class: "class",
    models.Enrollment: "enrollment",
    models.Schedule: "schedule",
    models.Room: "room",
    models.Location: "location",
    models.FaceEmbedding: "face",
    models.AttendanceSession: "session",
    models.AttendanceRecord: "attendance",
}

# Tao ban ghi diem danh la luong binh thuong (moi lan SV duoc nhan dien) - qua nhieu va
# khong phai "thao tac quan ly". Chi ghi khi co nguoi SUA ket qua.
_SKIP_CREATE = {models.AttendanceRecord}

# Cot nhay cam: chi ghi la co thay doi, khong bao gio ghi gia tri.
_SENSITIVE = {"password_hash", "embedding", "otp_hash", "token_hash"}
# Cot thay doi kem theo (dem phien ban token, moc thoi gian) - khong dang ghi rieng.
_NOISE = {"token_version", "credentials_changed_at", "checked_at", "opened_at"}


def set_actor(db: Session, user: models.User, request: Request | None) -> None:
    """Gan nguoi dang thao tac vao phien CSDL cua request (goi tu get_current_user)."""
    db.info["audit_actor"] = {
        "id": user.id, "email": user.email, "role": user.role,
        "ip": _client_ip(request),
    }


def _client_ip(request: Request | None) -> str | None:
    if request is None or request.client is None:
        return None
    return request.client.host


def record_event(db: Session, action: str, *, request: Request | None = None,
                 user: models.User | None = None, email: str | None = None,
                 success: bool = True, target_type: str | None = None,
                 target_id: int | None = None, target_label: str | None = None,
                 detail: dict | None = None) -> None:
    """Ghi tuong minh mot su kien khong lam doi du lieu (dang nhap, xuat bao cao...).
    Chi them vao phien - nguoi goi tu commit."""
    actor = db.info.get("audit_actor") or {}
    db.add(models.AuditLog(
        actor_id=user.id if user else actor.get("id"),
        actor_email=(user.email if user else None) or email or actor.get("email"),
        actor_role=user.role if user else actor.get("role"),
        action=action, success=success,
        target_type=target_type, target_id=target_id, target_label=target_label,
        faculty_id=_actor_faculty(db, user.id if user else actor.get("id"),
                                  user.role if user else actor.get("role")),
        ip=_client_ip(request) or actor.get("ip"),
        detail=json.dumps(detail, ensure_ascii=False) if detail else None,
    ))


# ------------------------------------------------------------------ ghi tu dong

@event.listens_for(Session, "after_flush")
def _audit_after_flush(session: Session, _flush_context) -> None:
    entries: list[tuple[str, object, dict | None]] = []
    for obj in session.new:
        if type(obj) in _TRACKED and type(obj) not in _SKIP_CREATE:
            entries.append(("create", obj, None))
    for obj in session.dirty:
        if type(obj) in _TRACKED:
            changes = _diff(obj)
            if changes:
                entries.append(("update", obj, changes))
    for obj in session.deleted:
        if type(obj) in _TRACKED:
            entries.append(("delete", obj, None))
    if not entries:
        return

    actor = session.info.get("audit_actor") or {}
    # Doi tuong them vao trong after_flush se duoc ghi o vong flush ke tiep cua cung lan
    # commit (commit flush lap lai cho toi khi sach).
    with session.no_autoflush:
        for op, obj, changes in entries:
            kind = _TRACKED[type(obj)]
            session.add(models.AuditLog(
                actor_id=actor.get("id"), actor_email=actor.get("email") or "he-thong",
                actor_role=actor.get("role") or "system",
                action=_action_name(kind, op, obj, changes),
                target_type=kind, target_id=getattr(obj, "id", None),
                target_label=_label(obj)[:255],
                faculty_id=_target_faculty(session, obj)
                or _actor_faculty(session, actor.get("id"), actor.get("role")),
                ip=actor.get("ip"),
                detail=json.dumps(changes, ensure_ascii=False) if changes else None,
            ))


def _diff(obj) -> dict:
    state = inspect(obj)
    changes: dict = {}
    for attr in state.mapper.column_attrs:
        history = state.attrs[attr.key].history
        if not history.has_changes() or attr.key in _NOISE:
            continue
        if attr.key in _SENSITIVE:
            changes[attr.key] = "(đã thay đổi)"
            continue
        old = history.deleted[0] if history.deleted else None
        new = history.added[0] if history.added else None
        changes[attr.key] = [_plain(old), _plain(new)]
    return changes


def _plain(value):
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    return str(value)


def _action_name(kind: str, op: str, obj, changes: dict | None) -> str:
    """Ten hanh dong de doc: mot so thay doi co y nghia rieng thi dat ten rieng."""
    if op == "update" and changes:
        if kind == "user" and "password_hash" in changes:
            return "user.password_changed"
        if kind == "student" and "consent_given" in changes:
            return "consent.given" if changes["consent_given"][1] else "consent.withdrawn"
        if kind == "face" and "status" in changes:
            return {"approved": "face.approved", "rejected": "face.rejected"}.get(
                changes["status"][1], "face.update")
        if kind == "session" and "status" in changes and changes["status"][1] == "closed":
            return "session.closed"
    if kind == "session" and op == "create":
        return "session.opened"
    return f"{kind}.{op}"


def _label(obj) -> str:
    """Nhan de doc, chi dung cot cua chinh doi tuong (khong nap quan he trong luc flush)."""
    match obj:
        case models.User():
            return obj.email
        case models.Unit():
            return f"{obj.code} - {obj.name}"
        case models.Student():
            return obj.student_code
        case models.Lecturer():
            return obj.lecturer_code
        case models.Class():
            return obj.class_code
        case models.Room():
            return obj.code
        case models.Location():
            return obj.code
        case models.Schedule():
            return f"lịch #{obj.id} (lớp #{obj.class_id}, thứ {obj.weekday + 2})"
        case models.Enrollment():
            return f"SV #{obj.student_id} ↔ lớp #{obj.class_id}"
        case models.FaceEmbedding():
            return f"khuôn mặt của SV #{obj.student_id}"
        case models.AttendanceSession():
            return f"phiên #{obj.id} ngày {obj.session_date}"
        case models.AttendanceRecord():
            return f"SV #{obj.student_id} - phiên #{obj.session_id}"
        case models.ParentStudent():
            return f"PH #{obj.parent_id} ↔ SV #{obj.student_id}"
        case models.Staff() | models.Parent():
            return f"tài khoản #{obj.user_id}"
    return f"#{getattr(obj, 'id', '?')}"


def _class_faculty(session: Session, class_id: int | None) -> int | None:
    if class_id is None:
        return None
    clazz = session.get(models.Class, class_id)
    return clazz.faculty_id if clazz else None


def _target_faculty(session: Session, obj) -> int | None:
    """Khoa ma doi tuong thuoc ve - de Lanh dao Khoa loc nhat ky cua Khoa minh."""
    if isinstance(obj, (models.Student, models.Lecturer, models.Class)):
        return obj.faculty_id
    if isinstance(obj, models.Unit) and obj.type == models.UNIT_FACULTY:
        return obj.id
    if isinstance(obj, (models.Schedule, models.Enrollment)):
        return _class_faculty(session, obj.class_id)
    if isinstance(obj, models.AttendanceSession):
        schedule = session.get(models.Schedule, obj.schedule_id)
        return _class_faculty(session, schedule.class_id) if schedule else None
    if isinstance(obj, models.AttendanceRecord):
        student = session.get(models.Student, obj.student_id)
        return student.faculty_id if student else None
    if isinstance(obj, models.FaceEmbedding):
        student = session.get(models.Student, obj.student_id)
        return student.faculty_id if student else None
    return None


def _actor_faculty(session: Session, user_id: int | None, role: str | None) -> int | None:
    """Khoa cua nguoi thao tac (can bo Khoa, giang vien) khi doi tuong khong cho biet Khoa."""
    if user_id is None:
        return None
    if role in models.FACULTY_ROLES:
        staff = session.query(models.Staff).filter_by(user_id=user_id).first()
        return staff.unit_id if staff else None
    if role == models.ROLE_LECTURER:
        lecturer = session.query(models.Lecturer).filter_by(user_id=user_id).first()
        return lecturer.faculty_id if lecturer else None
    return None
