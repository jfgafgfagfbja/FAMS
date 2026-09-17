from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app import schemas
from app.api.students import compute_student_attendance
from app.api.students import _to_out as student_to_out
from app.core.security import hash_password, require_roles
from app.db import models
from app.db.database import get_db

router = APIRouter(prefix="/parents", tags=["parents"])


def _to_out(p: models.Parent) -> schemas.ParentOut:
    return schemas.ParentOut(
        id=p.id, full_name=p.user.full_name, email=p.user.email, phone=p.phone,
        child_count=len(p.children),
    )


def _child_to_out(s: models.Student) -> schemas.ParentChildOut:
    base = student_to_out(s)
    classes = [
        schemas.MeClassBrief(id=e.clazz.id, class_code=e.clazz.class_code,
                             subject_name=e.clazz.subject_name, semester=e.clazz.semester)
        for e in s.enrollments
    ]
    return schemas.ParentChildOut(**base.model_dump(), classes=classes)


def _get_parent_or_404(db: Session, parent_id: int) -> models.Parent:
    parent = db.get(models.Parent, parent_id)
    if not parent:
        raise HTTPException(404, "Phu huynh khong ton tai")
    return parent


def _get_parent_by_user(db: Session, user: models.User) -> models.Parent:
    parent = db.query(models.Parent).filter_by(user_id=user.id).first()
    if not parent:
        raise HTTPException(404, "Khong tim thay ho so phu huynh")
    return parent


def _ensure_own_child(db: Session, parent: models.Parent, student_id: int) -> models.Student:
    link = (
        db.query(models.ParentStudent)
        .filter_by(parent_id=parent.id, student_id=student_id)
        .first()
    )
    if not link:
        raise HTTPException(403, "Ban khong duoc lien ket voi sinh vien nay")
    return link.student


# ---- Admin: quan ly tai khoan phu huynh (tao & lien ket thu cong, khong tu dang ky) ----

@router.post("", response_model=schemas.ParentOut,
             dependencies=[Depends(require_roles("admin"))])
def create_parent(body: schemas.ParentCreate, db: Session = Depends(get_db)):
    if db.query(models.User).filter(models.User.email == body.email).first():
        raise HTTPException(400, "Email da ton tai")
    user = models.User(email=body.email, password_hash=hash_password(body.password),
                       role="parent", full_name=body.full_name)
    db.add(user)
    db.flush()
    parent = models.Parent(user_id=user.id, phone=body.phone)
    db.add(parent)
    db.commit()
    db.refresh(parent)
    return _to_out(parent)


@router.get("", response_model=list[schemas.ParentOut],
            dependencies=[Depends(require_roles("admin"))])
def list_parents(
    response: Response,
    q: str | None = None,
    limit: int | None = None,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """Danh sach phu huynh, tim theo ten/email va phan trang - giong pattern
    list_students/list_lecturers (X-Total-Count qua header)."""
    query = db.query(models.Parent).join(models.User, models.Parent.user_id == models.User.id)
    if q:
        like = f"%{q}%"
        query = query.filter(or_(models.User.full_name.ilike(like),
                                 models.User.email.ilike(like)))

    response.headers["X-Total-Count"] = str(query.count())
    query = query.order_by(models.User.full_name).offset(offset)
    if limit is not None:
        query = query.limit(limit)
    return [_to_out(p) for p in query.all()]


@router.patch("/{parent_id}", response_model=schemas.ParentOut,
              dependencies=[Depends(require_roles("admin"))])
def update_parent(parent_id: int, body: schemas.ParentUpdate, db: Session = Depends(get_db)):
    parent = _get_parent_or_404(db, parent_id)
    data = body.model_dump(exclude_unset=True)
    if "full_name" in data:
        parent.user.full_name = data.pop("full_name")
    for field, value in data.items():
        setattr(parent, field, value)
    db.commit()
    db.refresh(parent)
    return _to_out(parent)


@router.delete("/{parent_id}", dependencies=[Depends(require_roles("admin"))])
def delete_parent(parent_id: int, db: Session = Depends(get_db)):
    parent = _get_parent_or_404(db, parent_id)
    user = parent.user
    db.delete(parent)
    db.delete(user)
    db.commit()
    return {"ok": True}


# ---- Phu huynh: xem con em ----
# QUAN TRONG: cac route "/me/..." phai khai bao TRUOC "/{parent_id}/..." o duoi -
# FastAPI khop route theo THU TU khai bao, neu de "/{parent_id}/children" truoc
# thi "/me/children" se bi no "nuot" nham (hieu parent_id="me") va tra ve 422.
@router.get("/me/children", response_model=list[schemas.ParentChildOut])
def my_children(
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles("parent")),
):
    parent = _get_parent_by_user(db, user)
    return [_child_to_out(link.student) for link in parent.children]


@router.get("/me/children/{student_id}/attendance",
            response_model=list[schemas.MyClassAttendanceOut])
def child_attendance(
    student_id: int,
    semester: str | None = None,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles("parent")),
):
    """Phu huynh xem chuyen can cua con: gom anh bang chung + gio + vi tri GPS
    (khi con tu diem danh bang selfie) cho tung buoi hoc - dung lai chinh logic
    tinh toan cua SV (compute_student_attendance) de dam bao du lieu nhat quan."""
    parent = _get_parent_by_user(db, user)
    student = _ensure_own_child(db, parent, student_id)
    return compute_student_attendance(db, student, semester)


# ---- Admin: quan ly lien ket phu huynh <-> sinh vien (dat SAU cac route "/me/...") ----

@router.get("/{parent_id}/children", response_model=list[schemas.StudentOut],
            dependencies=[Depends(require_roles("admin"))])
def list_parent_children(parent_id: int, db: Session = Depends(get_db)):
    parent = _get_parent_or_404(db, parent_id)
    return [student_to_out(link.student) for link in parent.children]


@router.post("/{parent_id}/children", dependencies=[Depends(require_roles("admin"))])
def link_child(parent_id: int, body: schemas.ParentLinkChild, db: Session = Depends(get_db)):
    """Admin lien ket phu huynh voi 1 SV bang MSSV (khong phai self-service:
    dung MSSV thay vi ID de admin khong phai tra cuu ID truoc)."""
    parent = _get_parent_or_404(db, parent_id)
    student = db.query(models.Student).filter_by(student_code=body.student_code).first()
    if not student:
        raise HTTPException(404, f"Khong tim thay sinh vien voi MSSV {body.student_code}")
    existed = (
        db.query(models.ParentStudent)
        .filter_by(parent_id=parent.id, student_id=student.id)
        .first()
    )
    if existed:
        raise HTTPException(400, "Da lien ket voi sinh vien nay roi")
    db.add(models.ParentStudent(parent_id=parent.id, student_id=student.id))
    db.commit()
    return {"ok": True}


@router.delete("/{parent_id}/children/{student_id}",
               dependencies=[Depends(require_roles("admin"))])
def unlink_child(parent_id: int, student_id: int, db: Session = Depends(get_db)):
    link = (
        db.query(models.ParentStudent)
        .filter_by(parent_id=parent_id, student_id=student_id)
        .first()
    )
    if not link:
        raise HTTPException(404, "Chua lien ket voi sinh vien nay")
    db.delete(link)
    db.commit()
    return {"ok": True}
