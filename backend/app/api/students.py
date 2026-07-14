from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app import schemas
from app.core.config import settings
from app.core.security import get_current_user, hash_password, require_roles
from app.db import models
from app.db.database import get_db

router = APIRouter(prefix="/students", tags=["students"])


def _get_student_or_404(db: Session, student_id: int) -> models.Student:
    student = db.get(models.Student, student_id)
    if not student:
        raise HTTPException(404, "Sinh vien khong ton tai")
    return student


@router.post("", response_model=schemas.StudentOut,
             dependencies=[Depends(require_roles("admin"))])
def create_student(body: schemas.StudentCreate, db: Session = Depends(get_db)):
    if db.query(models.User).filter(models.User.email == body.email).first():
        raise HTTPException(400, "Email da ton tai")
    user = models.User(email=body.email, password_hash=hash_password(body.password),
                       role="student", full_name=body.full_name)
    db.add(user)
    db.flush()
    student = models.Student(user_id=user.id, student_code=body.student_code,
                             major=body.major, cohort=body.cohort)
    db.add(student)
    db.commit()
    db.refresh(student)
    return _to_out(student)


@router.get("", response_model=list[schemas.StudentOut],
            dependencies=[Depends(require_roles("admin", "lecturer"))])
def list_students(
    response: Response,
    q: str | None = None,
    limit: int | None = None,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """Danh sach SV, loc theo q (MSSV hoac ho ten) va phan trang qua limit/offset.
    Khong truyen limit -> tra ve toan bo (giu tuong thich voi cac noi dang dung
    danh sach day du, vd dropdown ghi danh). Tong so ban ghi tra qua header
    X-Total-Count de FE dung cho phan trang ma khong doi shape response cu."""
    query = db.query(models.Student).join(models.User, models.Student.user_id == models.User.id)
    if q:
        like = f"%{q}%"
        query = query.filter(or_(models.Student.student_code.ilike(like),
                                 models.User.full_name.ilike(like)))

    response.headers["X-Total-Count"] = str(query.count())
    query = query.order_by(models.Student.student_code).offset(offset)
    if limit is not None:
        query = query.limit(limit)
    return [_to_out(s) for s in query.all()]


@router.get("/me", response_model=schemas.StudentOut)
def get_my_student_record(
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    if user.role != "student":
        raise HTTPException(403, "Chi sinh vien moi co ho so nay")
    student = db.query(models.Student).filter_by(user_id=user.id).first()
    if not student:
        raise HTTPException(404, "Khong tim thay ho so sinh vien")
    return _to_out(student)


@router.get("/me/attendance", response_model=list[schemas.MyClassAttendanceOut])
def get_my_attendance(
    semester: str | None = None,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """Chuyen can chi tiet cua chinh SV dang dang nhap, loc theo hoc ky (Class.semester,
    dang luu dang "YYYY.N"). Khong truyen semester -> lay hoc ky moi nhat (so sanh chuoi)
    trong cac lop da ghi danh. Gom san danh sach tung buoi hoc de FE mo rong chi tiet
    (ngay, trang thai, gio ghi nhan, anh bang chung) trong 1 lan goi, tranh N+1."""
    if user.role != "student":
        raise HTTPException(403, "Chi sinh vien moi xem duoc muc nay")
    student = db.query(models.Student).filter_by(user_id=user.id).first()
    if not student:
        raise HTTPException(404, "Khong tim thay ho so sinh vien")

    enrollments = student.enrollments
    if not enrollments:
        return []

    target_semester = semester or max((e.clazz.semester for e in enrollments), default=None)
    if not target_semester:
        return []

    result = []
    for enrollment in enrollments:
        clazz = enrollment.clazz
        if clazz.semester != target_semester:
            continue

        sessions = (
            db.query(models.AttendanceSession)
            .join(models.Schedule)
            .filter(models.Schedule.class_id == clazz.id,
                    models.AttendanceSession.status == "closed")
            .order_by(models.AttendanceSession.session_date)
            .all()
        )
        records_by_session = {}
        if sessions:
            records_by_session = {
                r.session_id: r
                for r in db.query(models.AttendanceRecord)
                .filter(models.AttendanceRecord.session_id.in_([s.id for s in sessions]),
                        models.AttendanceRecord.student_id == student.id)
                .all()
            }

        counts = {"present": 0, "late": 0, "absent": 0, "excused": 0, "manual": 0}
        session_details = []
        for s in sessions:
            r = records_by_session.get(s.id)
            if r:
                counts[r.status] = counts.get(r.status, 0) + 1
            session_details.append(schemas.MyAttendanceSessionOut(
                session_id=s.id, session_date=s.session_date,
                status=r.status if r else None,
                checked_at=r.checked_at if r else None,
                confidence=r.confidence if r else None,
                evidence_image=r.evidence_image if r else None,
                record_id=r.id if r else None,
            ))

        total_sessions = len(sessions)
        absent_ratio = counts["absent"] / total_sessions if total_sessions else 0
        lecturer = db.get(models.Lecturer, clazz.lecturer_id)
        result.append(schemas.MyClassAttendanceOut(
            class_id=clazz.id, class_code=clazz.class_code, subject_name=clazz.subject_name,
            semester=clazz.semester, lecturer_name=lecturer.user.full_name,
            lecturer_email=lecturer.user.email,
            **counts, total_sessions=total_sessions, absent_ratio=absent_ratio,
            warn_ratio=settings.ABSENCE_WARN_RATIO,
            warning=absent_ratio >= settings.ABSENCE_WARN_RATIO,
            sessions=session_details,
        ))
    return result


@router.get("/{student_id}", response_model=schemas.StudentOut,
            dependencies=[Depends(require_roles("admin", "lecturer"))])
def get_student(student_id: int, db: Session = Depends(get_db)):
    return _to_out(_get_student_or_404(db, student_id))


@router.patch("/{student_id}", response_model=schemas.StudentOut,
              dependencies=[Depends(require_roles("admin"))])
def update_student(student_id: int, body: schemas.StudentUpdate, db: Session = Depends(get_db)):
    student = _get_student_or_404(db, student_id)
    data = body.model_dump(exclude_unset=True)
    if "full_name" in data:
        student.user.full_name = data.pop("full_name")
    for field, value in data.items():
        setattr(student, field, value)
    db.commit()
    db.refresh(student)
    return _to_out(student)


@router.delete("/{student_id}", dependencies=[Depends(require_roles("admin"))])
def delete_student(student_id: int, db: Session = Depends(get_db)):
    student = _get_student_or_404(db, student_id)
    if student.enrollments or student.embeddings:
        raise HTTPException(
            409, "Sinh vien da co du lieu dang ky lop/khuon mat, khong the xoa truc tiep")
    user = student.user
    db.delete(student)
    db.delete(user)
    db.commit()
    return {"ok": True}


@router.post("/{student_id}/consent")
def give_consent(
    student_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """Xac nhan dong y cho phep thu thap du lieu khuon mat. Chi admin hoac chinh SV do."""
    student = _get_student_or_404(db, student_id)
    is_self = user.role == "student" and student.user_id == user.id
    if not is_self and user.role != "admin":
        raise HTTPException(403, "Chi sinh vien hoac admin moi xac nhan duoc dong y")
    student.consent_given = True
    student.consent_given_at = datetime.now()
    db.commit()
    return {"ok": True, "consent_given": True}


def _to_out(s: models.Student) -> schemas.StudentOut:
    return schemas.StudentOut(
        id=s.id, student_code=s.student_code, full_name=s.user.full_name,
        major=s.major, cohort=s.cohort, face_enrolled=len(s.embeddings) > 0,
        consent_given=s.consent_given,
    )
