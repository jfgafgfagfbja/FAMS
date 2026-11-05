"""Can bo dat lai mat khau cho nguoi khac: admin moi tai khoan, P.CTSV cho SV va phu huynh."""
import pytest

from app.core.security import hash_password
from app.db import models
from tests.conftest import auth_headers, login

NEW = "MatKhauMoi#2026"


@pytest.fixture()
def org(db_session, seed):
    """Du cac vai tro can bo, mot phu huynh, va id ho so de goi endpoint."""
    db = db_session
    units = {
        "training_office": models.Unit(code="P-DT", name="Phong DT", type=models.UNIT_TRAINING),
        "student_affairs": models.Unit(code="P-CTSV", name="Phong CTSV", type=models.UNIT_AFFAIRS),
        "faculty_office": models.Unit(code="K-CNTT", name="Khoa CNTT", type=models.UNIT_FACULTY),
        "board": models.Unit(code="B-TT", name="Ban TT", type=models.UNIT_BOARD),
    }
    db.add_all(units.values())
    db.flush()
    units["faculty_leader"] = units["faculty_office"]

    staff_ids = {}
    for role, unit in units.items():
        user = models.User(email=f"{role}@test.local", password_hash=hash_password("staff123"),
                           role=role, full_name=role)
        db.add(user)
        db.flush()
        staff = models.Staff(user_id=user.id, unit_id=unit.id, position="Chuyen vien")
        db.add(staff)
        db.flush()
        staff_ids[role] = staff.id

    parent_user = models.User(email="ph1@test.local", password_hash=hash_password("ph123456"),
                              role="parent", full_name="Phu huynh")
    db.add(parent_user)
    db.flush()
    parent = models.Parent(user_id=parent_user.id)
    db.add(parent)
    db.flush()
    db.add(models.ParentStudent(parent_id=parent.id, student_id=seed["sv1_id"]))
    db.commit()

    lecturer = (db.query(models.Lecturer).join(models.User, models.User.id == models.Lecturer.user_id)
                .filter(models.User.email == "gv1@test.local").one())
    return {"staff": staff_ids, "parent_id": parent.id, "lecturer_id": lecturer.id}


def _admin(client):
    return auth_headers(login(client, "admin@test.local", "admin123"))


def _staff(client, role):
    return auth_headers(login(client, f"{role}@test.local", "staff123"))


def _reset(client, headers, path, password=NEW):
    return client.post(f"{path}/reset-password", json={"new_password": password}, headers=headers)


def _can_login(client, email, password):
    return client.post("/auth/login", data={"username": email, "password": password}).status_code == 200


# ---- Doi duoc mat khau ----

def test_admin_resets_student_password(client, seed):
    resp = _reset(client, _admin(client), f"/students/{seed['sv1_id']}")
    assert resp.status_code == 200, resp.text
    assert _can_login(client, "sv1@test.local", NEW)
    assert not _can_login(client, "sv1@test.local", "sv123")


def test_admin_resets_every_kind_of_account(client, seed, org):
    admin = _admin(client)
    cases = [
        (f"/parents/{org['parent_id']}", "ph1@test.local"),
        (f"/lecturers/{org['lecturer_id']}", "gv1@test.local"),
        (f"/staff/{org['staff']['student_affairs']}", "student_affairs@test.local"),
    ]
    for path, email in cases:
        assert _reset(client, admin, path).status_code == 200, path
        assert _can_login(client, email, NEW), email


def test_student_affairs_resets_student_and_parent(client, seed, org):
    ctsv = _staff(client, "student_affairs")
    assert _reset(client, ctsv, f"/students/{seed['sv1_id']}").status_code == 200
    assert _reset(client, ctsv, f"/parents/{org['parent_id']}").status_code == 200
    assert _can_login(client, "sv1@test.local", NEW)
    assert _can_login(client, "ph1@test.local", NEW)


# ---- Khong ai khac duoc doi ----

def test_student_affairs_cannot_reset_lecturer_or_staff(client, seed, org):
    ctsv = _staff(client, "student_affairs")
    assert _reset(client, ctsv, f"/lecturers/{org['lecturer_id']}").status_code == 403
    assert _reset(client, ctsv, f"/staff/{org['staff']['training_office']}").status_code == 403
    assert _can_login(client, "gv1@test.local", "gv123")


@pytest.mark.parametrize("role", ["training_office", "faculty_office", "faculty_leader", "board"])
def test_other_staff_cannot_reset_anyone(client, seed, org, role):
    headers = _staff(client, role)
    for path in (f"/students/{seed['sv1_id']}", f"/parents/{org['parent_id']}",
                 f"/lecturers/{org['lecturer_id']}", f"/staff/{org['staff']['board']}"):
        assert _reset(client, headers, path).status_code == 403, path


def test_lecturer_cannot_reset_student(client, seed):
    headers = auth_headers(login(client, "gv1@test.local", "gv123"))
    assert _reset(client, headers, f"/students/{seed['sv1_id']}").status_code == 403


def test_student_cannot_reset_another_student_or_bypass_current_password(client, seed):
    headers = auth_headers(login(client, "sv1@test.local", "sv123"))
    assert _reset(client, headers, f"/students/{seed['sv2_id']}").status_code == 403
    assert _reset(client, headers, f"/students/{seed['sv1_id']}").status_code == 403


def test_needs_login(client, seed):
    resp = client.post(f"/students/{seed['sv1_id']}/reset-password", json={"new_password": NEW})
    assert resp.status_code == 401


# ---- Tac dong sau khi doi ----

def test_reset_signs_person_out_everywhere(client, seed):
    session = client.post("/auth/login", data={"username": "sv1@test.local", "password": "sv123"}).json()
    old_headers = auth_headers(session["access_token"])
    assert client.get("/auth/me", headers=old_headers).status_code == 200

    assert _reset(client, _admin(client), f"/students/{seed['sv1_id']}").status_code == 200

    assert client.get("/auth/me", headers=old_headers).status_code == 401
    refresh = client.post("/auth/refresh", json={"refresh_token": session["refresh_token"]})
    assert refresh.status_code == 401


def test_reset_unlocks_locked_account(client, seed):
    from app.core.config import settings

    for _ in range(settings.LOGIN_MAX_FAILED_PER_ACCOUNT):
        client.post("/auth/login", data={"username": "sv1@test.local", "password": "sai-mat-khau"})
    locked = client.post("/auth/login", data={"username": "sv1@test.local", "password": "sv123"})
    assert locked.status_code == 429

    admin = _admin(client)
    assert _reset(client, admin, f"/students/{seed['sv1_id']}").status_code == 200
    assert _can_login(client, "sv1@test.local", NEW)


def test_reset_cancels_pending_otp(client, db_session, seed):
    from datetime import datetime, timedelta

    user = db_session.get(models.Student, seed["sv1_id"]).user
    db_session.add(models.PasswordReset(user_id=user.id, otp_hash=hash_password("123456"),
                                        expires_at=datetime.utcnow() + timedelta(minutes=10)))
    db_session.commit()

    assert _reset(client, _admin(client), f"/students/{seed['sv1_id']}").status_code == 200

    resp = client.post("/auth/reset-password", json={"email": "sv1@test.local", "otp": "123456",
                                                     "new_password": "MatKhauKhac#1"})
    assert resp.status_code == 400
    assert _can_login(client, "sv1@test.local", NEW)


def test_short_password_rejected(client, seed):
    resp = _reset(client, _admin(client), f"/students/{seed['sv1_id']}", password="ngan")
    assert resp.status_code == 422
    assert _can_login(client, "sv1@test.local", "sv123")


def test_unknown_account_is_404(client, seed):
    admin = _admin(client)
    for path in ("/students/999999", "/parents/999999", "/lecturers/999999", "/staff/999999"):
        assert _reset(client, admin, path).status_code == 404, path


def test_reset_is_logged_without_the_password(client, db_session, seed, org):
    ctsv = _staff(client, "student_affairs")
    assert _reset(client, ctsv, f"/students/{seed['sv1_id']}").status_code == 200

    entry = (db_session.query(models.AuditLog)
             .filter_by(action="user.password_changed", target_label="sv1@test.local").one())
    assert entry.actor_email == "student_affairs@test.local"
    assert entry.actor_role == "student_affairs"
    assert "đã thay đổi" in entry.detail
    assert NEW not in entry.detail
