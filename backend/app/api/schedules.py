from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, Response
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app import schemas
from app.core.config import settings
from app.core.security import get_current_user, require_roles
from app.db import models
from app.db.database import get_db

router = APIRouter(prefix="/schedules", tags=["schedules"])


def open_from_time(start: time) -> time:
    """Gio som nhat duoc mo phien cho tiet bat dau luc `start`
    (= start - EARLY_OPEN_MINUTES). Dung chung cho cac response tra lich ve FE."""
    anchor = datetime.combine(date(2000, 1, 1), start)
    return (anchor - timedelta(minutes=settings.EARLY_OPEN_MINUTES)).time()


@router.get("", response_model=list[schemas.ScheduleWithClassOut],
            dependencies=[Depends(require_roles("admin"))])
def list_all_schedules(
    response: Response,
    q: str | None = None,
    limit: int | None = None,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """Toan bo lich hoc cua truong kem thong tin lop (dung cho trang quan tri
    /admin/schedules) - loc theo q (ma lop/ten mon/phong), phan trang qua
    limit/offset, tong so ban ghi tra qua header X-Total-Count."""
    query = db.query(models.Schedule).join(models.Class)
    if q:
        like = f"%{q}%"
        query = query.filter(or_(models.Class.class_code.ilike(like),
                                 models.Class.subject_name.ilike(like),
                                 models.Schedule.room.ilike(like)))

    response.headers["X-Total-Count"] = str(query.count())
    query = query.order_by(models.Class.class_code, models.Schedule.weekday).offset(offset)
    if limit is not None:
        query = query.limit(limit)

    return [
        schemas.ScheduleWithClassOut(
            id=s.id, class_id=s.class_id, class_code=s.clazz.class_code,
            subject_name=s.clazz.subject_name, weekday=s.weekday,
            start_time=s.start_time, end_time=s.end_time, room=s.room,
        )
        for s in query.all()
    ]


@router.get("/week", response_model=list[schemas.WeekSlotOut])
def week_schedule(
    start: date | None = None,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """Lich hoc/day theo tuan (Thu 2 - CN) cua user dang dang nhap, gop san trang
    thai phien diem danh + ket qua tuong ung (neu co) trong 1 lan goi - tranh FE
    phai goi rieng tung buoi (N+1). SV: theo lop da ghi danh. GV: theo lop dang
    day. Admin: xem toan bo lich cua truong (giong cach /classes tra ve cho admin)."""
    base = start or date.today()
    monday = base - timedelta(days=base.weekday())
    week_dates = [monday + timedelta(days=i) for i in range(7)]

    if user.role == "student":
        student = db.query(models.Student).filter_by(user_id=user.id).first()
        class_ids = [e.class_id for e in student.enrollments] if student else []
    elif user.role == "lecturer":
        lecturer = db.query(models.Lecturer).filter_by(user_id=user.id).first()
        class_ids = (
            [c.id for c in db.query(models.Class).filter_by(lecturer_id=lecturer.id).all()]
            if lecturer else []
        )
    else:
        class_ids = [c.id for c in db.query(models.Class).all()]

    if not class_ids:
        return []

    classes_by_id = {
        c.id: c for c in db.query(models.Class).filter(models.Class.id.in_(class_ids)).all()
    }
    schedules = (
        db.query(models.Schedule)
        .filter(models.Schedule.class_id.in_(class_ids))
        .all()
    )
    if not schedules:
        return []

    sessions = (
        db.query(models.AttendanceSession)
        .filter(models.AttendanceSession.schedule_id.in_([s.id for s in schedules]),
                models.AttendanceSession.session_date.in_(week_dates))
        .all()
    )
    session_by_key = {(s.schedule_id, s.session_date): s for s in sessions}
    session_ids = [s.id for s in sessions]

    # SV: trang thai diem danh cua chinh minh cho cac phien trong tuan nay.
    my_status_by_session: dict[int, str] = {}
    if user.role == "student" and session_ids:
        student = db.query(models.Student).filter_by(user_id=user.id).first()
        if student:
            recs = (
                db.query(models.AttendanceRecord)
                .filter(models.AttendanceRecord.session_id.in_(session_ids),
                        models.AttendanceRecord.student_id == student.id)
                .all()
            )
            my_status_by_session = {r.session_id: r.status for r in recs}

    # GV: so SV co mat khi phien da dong + tong so SV ghi danh lop (mot lan truy van cho ca tuan).
    present_count_by_session: dict[int, int] = {}
    total_count_by_class: dict[int, int] = {}
    if user.role == "lecturer":
        closed_ids = [s.id for s in sessions if s.status == "closed"]
        if closed_ids:
            rows = (
                db.query(models.AttendanceRecord.session_id, func.count())
                .filter(models.AttendanceRecord.session_id.in_(closed_ids),
                        models.AttendanceRecord.status.in_(("present", "late", "manual")))
                .group_by(models.AttendanceRecord.session_id)
                .all()
            )
            present_count_by_session = dict(rows)
        rows = (
            db.query(models.Enrollment.class_id, func.count())
            .filter(models.Enrollment.class_id.in_(class_ids))
            .group_by(models.Enrollment.class_id)
            .all()
        )
        total_count_by_class = dict(rows)

    result = []
    for d in week_dates:
        weekday = d.weekday()
        for sch in schedules:
            if sch.weekday != weekday:
                continue
            clazz = classes_by_id[sch.class_id]
            session = session_by_key.get((sch.id, d))
            entry = schemas.WeekSlotOut(
                date=d, weekday=weekday, schedule_id=sch.id, class_id=clazz.id,
                class_code=clazz.class_code, subject_name=clazz.subject_name,
                room=sch.room, start_time=sch.start_time, end_time=sch.end_time,
                open_from=open_from_time(sch.start_time),
                session_id=session.id if session else None,
                session_status=session.status if session else None,
            )
            if session:
                entry.my_status = my_status_by_session.get(session.id)
                if session.status == "closed":
                    entry.present_count = present_count_by_session.get(session.id, 0)
                    entry.total_count = total_count_by_class.get(clazz.id, 0)
            result.append(entry)

    result.sort(key=lambda e: (e.date, e.start_time))
    return result
