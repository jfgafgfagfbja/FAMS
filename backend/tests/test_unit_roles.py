"""Phan quyen Phong Dao tao, Phong CTSV, Khoa, Ban nganh (xem ma tran o core/authz.py)."""
from datetime import date

import pytest

from app.core.security import hash_password
from app.db import models
from tests.conftest import auth_headers, login


@pytest.fixture()
def org(db_session, seed):
    """2 Khoa + P.DT + P.CTSV + 1 Ban; class1/sv1/gv1 thuoc Khoa CNTT, class2/sv2 thuoc Khoa KT."""
    db = db_session
    cntt = models.Unit(code="K-CNTT", name="Khoa CNTT", type="faculty")
    kt = models.Unit(code="K-KT", name="Khoa Kien truc", type="faculty")
    pdt = models.Unit(code="P-DT", name="Phong Dao tao", type="training")
    ctsv = models.Unit(code="P-CTSV", name="Phong CTSV", type="student_affairs")
    ban = models.Unit(code="B-TT", name="Ban Thanh tra", type="board")
    db.add_all([cntt, kt, pdt, ctsv, ban])
    db.flush()

    accounts = {
        "pdt@test.local": (pdt, "training_office"),
        "ctsv@test.local": (ctsv, "student_affairs"),
        "khoa.cntt@test.local": (cntt, "faculty_office"),
        "khoa.kt@test.local": (kt, "faculty_office"),
        "ldk.cntt@test.local": (cntt, "faculty_leader"),
        "ldk.kt@test.local": (kt, "faculty_leader"),
        "ban@test.local": (ban, "board"),
    }
    for email, (unit, role) in accounts.items():
        user = models.User(email=email, password_hash=hash_password("staff123"),
                           role=role, full_name=email.split("@")[0])
        db.add(user)
        db.flush()
        db.add(models.Staff(user_id=user.id, unit_id=unit.id, position="Chuyen vien"))

    db.get(models.Class, seed["class1_id"]).faculty_id = cntt.id
    db.get(models.Class, seed["class2_id"]).faculty_id = kt.id
    db.get(models.Student, seed["sv1_id"]).faculty_id = cntt.id
    db.get(models.Student, seed["sv2_id"]).faculty_id = kt.id
    db.commit()
    return {"cntt_id": cntt.id, "kt_id": kt.id, "pdt_id": pdt.id, "ctsv_id": ctsv.id,
            "ban_id": ban.id}


def _h(client, email, password="staff123"):
    return auth_headers(login(client, email, password))


def _closed_session_with_absent(db_session, seed):
    session = models.AttendanceSession(
        schedule_id=seed["schedule1_id"], session_date=date(2026, 1, 5), status="closed")
    db_session.add(session)
    db_session.flush()
    record = models.AttendanceRecord(session_id=session.id, student_id=seed["sv1_id"],
                                     status="absent")
    db_session.add(record)
    db_session.commit()
    return session.id, record.id


# ---------------- /auth/me ----------------

def test_me_returns_unit_for_staff(client, seed, org):
    resp = client.get("/auth/me", headers=_h(client, "khoa.cntt@test.local"))
    assert resp.status_code == 200
    body = resp.json()
    assert body["role"] == "faculty_office"
    assert body["unit_name"] == "Khoa CNTT"
    assert body["unit_type"] == "faculty"


# ---------------- Phong Dao tao: hoc vu ----------------

def test_training_office_manages_classes_and_schedules(client, seed, org):
    h = _h(client, "pdt@test.local")
    lecturers = client.get("/lecturers", headers=h).json()
    resp = client.post("/classes", json={
        "class_code": "C9", "subject_name": "Mon 9", "lecturer_id": lecturers[0]["id"],
        "semester": "2026.1", "faculty_id": org["cntt_id"]}, headers=h)
    assert resp.status_code == 200, resp.text
    class_id = resp.json()["id"]
    assert resp.json()["faculty_name"] == "Khoa CNTT"

    resp = client.post("/classes/schedules", json={
        "class_id": class_id, "weekday": 2, "start_time": "07:00:00",
        "end_time": "09:00:00", "room": "A1"}, headers=h)
    assert resp.status_code == 200
    assert client.post(f"/classes/{class_id}/enroll/{seed['sv1_id']}", headers=h).status_code == 200


def test_training_office_cannot_manage_students_or_faces(client, seed, org):
    h = _h(client, "pdt@test.local")
    resp = client.post("/students", json={
        "email": "x@fams.edu.vn", "password": "12345678", "full_name": "X",
        "student_code": "SV9999"}, headers=h)
    assert resp.status_code == 403
    assert client.get("/students", headers=h).status_code == 200  # nhung duoc xem
    assert client.get("/faces/pending", headers=h).status_code == 403


# ---------------- Phong CTSV: ho so SV, khuon mat, co phep ----------------

def test_student_affairs_manages_students_but_not_classes(client, seed, org):
    h = _h(client, "ctsv@test.local")
    resp = client.post("/students", json={
        "email": "moi@fams.edu.vn", "password": "12345678", "full_name": "SV Moi",
        "student_code": "SV0100", "faculty_id": org["cntt_id"]}, headers=h)
    assert resp.status_code == 200, resp.text
    assert client.get("/faces/pending", headers=h).status_code == 200
    assert client.get("/classes", headers=h).status_code == 200  # xem lop
    resp = client.post("/classes", json={
        "class_code": "C8", "subject_name": "Mon 8", "lecturer_id": 1, "semester": "2026.1"},
        headers=h)
    assert resp.status_code == 403


def test_student_affairs_can_excuse_but_not_mark_present(client, db_session, seed, org):
    session_id, record_id = _closed_session_with_absent(db_session, seed)
    h = _h(client, "ctsv@test.local")

    resp = client.patch(f"/sessions/{session_id}/records/{record_id}",
                        json={"status": "present", "reason": "thu"}, headers=h)
    assert resp.status_code == 403

    resp = client.patch(f"/sessions/{session_id}/records/{record_id}",
                        json={"status": "excused", "reason": "Don xin phep so 12"}, headers=h)
    assert resp.status_code == 200
    assert resp.json()["status"] == "excused"

    resp = client.patch(f"/sessions/{session_id}/records/{record_id}",
                        json={"status": "absent", "reason": "Huy duyet nham"}, headers=h)
    assert resp.status_code == 200


# ---------------- Khoa: chi trong pham vi Khoa ----------------

def test_faculty_office_sees_only_own_faculty(client, seed, org):
    h = _h(client, "khoa.cntt@test.local")
    classes = client.get("/classes", headers=h).json()
    assert [c["id"] for c in classes] == [seed["class1_id"]]
    students = client.get("/students", headers=h).json()
    assert [s["id"] for s in students] == [seed["sv1_id"]]

    assert client.get(f"/classes/{seed['class2_id']}/students", headers=h).status_code == 403
    assert client.get(f"/students/{seed['sv2_id']}", headers=h).status_code == 403
    assert client.get(f"/reports/attendance/{seed['class1_id']}", headers=h).status_code == 200
    assert client.get(f"/reports/attendance/{seed['class2_id']}", headers=h).status_code == 403


def test_faculty_office_edits_only_own_faculty_classes(client, seed, org):
    """Van phong Khoa nhap lieu lop/lich/ghi danh - nhung chi trong Khoa minh."""
    h = _h(client, "khoa.cntt@test.local")
    assert client.patch(f"/classes/{seed['class1_id']}", json={"subject_name": "Doi"},
                        headers=h).status_code == 200                      # lop CNTT
    assert client.patch(f"/classes/{seed['class2_id']}", json={"subject_name": "Doi"},
                        headers=h).status_code == 403                      # lop Kien truc
    assert client.post("/classes/schedules", json={
        "class_id": seed["class2_id"], "weekday": 2, "room": "A1",
        "start_time": "07:00:00", "end_time": "09:00:00"}, headers=h).status_code == 403
    assert client.post(f"/classes/{seed['class1_id']}/enroll/{seed['sv2_id']}",
                       headers=h).status_code == 200
    # Ho so sinh vien van la viec cua P.CTSV.
    assert client.patch(f"/students/{seed['sv1_id']}", json={"major": "Doi"},
                        headers=h).status_code == 403


def test_faculty_office_new_class_always_in_own_faculty(client, db_session, seed, org):
    h = _h(client, "khoa.cntt@test.local")
    lecturer_id = db_session.query(models.Lecturer).first().id
    body = {"class_code": "CNTT-01", "subject_name": "Mon moi", "semester": "2026.1",
            "lecturer_id": lecturer_id}
    resp = client.post("/classes", json=body, headers=h)
    assert resp.status_code == 200, resp.text
    assert resp.json()["faculty_id"] == org["cntt_id"]
    other = client.post("/classes", json={**body, "class_code": "KT-01", "faculty_id": org["kt_id"]},
                        headers=h)
    assert other.status_code == 403


def test_faculty_office_no_longer_approves_excuses(client, db_session, seed, org):
    """Phe duyet la viec cua Lanh dao Khoa, khong phai giao vu."""
    session_id, record_id = _closed_session_with_absent(db_session, seed)
    resp = client.patch(f"/sessions/{session_id}/records/{record_id}",
                        json={"status": "excused", "reason": "x"},
                        headers=_h(client, "khoa.cntt@test.local"))
    assert resp.status_code == 403


def test_faculty_leader_excuse_scoped_to_faculty(client, db_session, seed, org):
    session_id, record_id = _closed_session_with_absent(db_session, seed)  # sv1, class1: CNTT

    other = client.patch(f"/sessions/{session_id}/records/{record_id}",
                         json={"status": "excused", "reason": "x"},
                         headers=_h(client, "ldk.kt@test.local"))
    assert other.status_code == 403

    own = client.patch(f"/sessions/{session_id}/records/{record_id}",
                       json={"status": "excused", "reason": "Don cua Khoa"},
                       headers=_h(client, "ldk.cntt@test.local"))
    assert own.status_code == 200


def test_faculty_leader_supervises_but_does_not_enter_data(client, seed, org):
    h = _h(client, "ldk.cntt@test.local")
    # Xem duoc du lieu cua Khoa minh...
    classes = client.get("/classes", headers=h).json()
    assert [c["class_code"] for c in classes] == ["C1"]
    assert client.get(f"/reports/attendance/{seed['class1_id']}", headers=h).status_code == 200
    assert client.get("/reports/overview", headers=h).json()["scope"] == "faculty"
    # ...nhung khong nhap lieu.
    assert client.patch(f"/classes/{seed['class1_id']}", json={"subject_name": "Doi"},
                        headers=h).status_code == 403
    assert client.post("/classes", json={"class_code": "X", "subject_name": "X",
                                         "semester": "2026.1"}, headers=h).status_code == 403
    assert client.get(f"/classes/{seed['class2_id']}", headers=h).status_code == 403


def test_admin_creates_faculty_leader_account(client, seed, org):
    admin = auth_headers(login(client, "admin@test.local", "admin123"))
    resp = client.post("/staff", json={"email": "truongkhoa@fams.edu.vn", "password": "truongkhoa1",
                                       "full_name": "Truong khoa", "unit_id": org["cntt_id"],
                                       "position": "Truong khoa", "faculty_leader": True},
                       headers=admin)
    assert resp.status_code == 200, resp.text
    assert resp.json()["role"] == "faculty_leader"

    bad = client.post("/staff", json={"email": "x@fams.edu.vn", "password": "abcdefgh1",
                                      "full_name": "X", "unit_id": org["pdt_id"], "faculty_leader": True},
                      headers=admin)
    assert bad.status_code == 400


def test_staff_can_view_student_attendance_detail(client, db_session, seed, org):
    _closed_session_with_absent(db_session, seed)
    resp = client.get(f"/students/{seed['sv1_id']}/attendance", params={"semester": "2026.1"},
                      headers=_h(client, "khoa.cntt@test.local"))
    assert resp.status_code == 200
    assert resp.json()[0]["absent"] == 1
    assert resp.json()[0]["sessions"][0]["record_id"]


# ---------------- Ban nganh: chi thong ke tong hop ----------------

def test_board_only_sees_aggregated_overview(client, db_session, seed, org):
    _closed_session_with_absent(db_session, seed)
    h = _h(client, "ban@test.local")
    for url in ("/students", "/classes", "/lecturers", "/sessions",
                f"/reports/attendance/{seed['class1_id']}"):
        assert client.get(url, headers=h).status_code == 403, url

    resp = client.get("/reports/overview", headers=h)
    assert resp.status_code == 200
    body = resp.json()
    assert body["scope"] == "school"
    assert body["semester"] == "2026.1"
    assert body["totals"]["absent"] == 1
    assert body["totals"]["classes"] == 2
    assert {row["faculty_name"] for row in body["by_faculty"]} == {"Khoa CNTT", "Khoa Kien truc"}
    assert "full_name" not in str(body)


def test_faculty_overview_limited_to_own_faculty(client, seed, org):
    body = client.get("/reports/overview", headers=_h(client, "khoa.kt@test.local")).json()
    assert body["scope"] == "faculty"
    assert body["scope_name"] == "Khoa Kien truc"
    assert body["totals"]["classes"] == 1
    assert [row["faculty_name"] for row in body["by_faculty"]] == ["Khoa Kien truc"]


def test_student_and_parent_cannot_see_overview(client, seed, org):
    h = auth_headers(login(client, "sv1@test.local", "sv123"))
    assert client.get("/reports/overview", headers=h).status_code == 403


# ---------------- Admin: don vi & tai khoan can bo ----------------

def test_admin_creates_staff_with_role_from_unit(client, seed, org):
    h = auth_headers(login(client, "admin@test.local", "admin123"))
    resp = client.post("/staff", json={
        "email": "cb.moi@fams.edu.vn", "password": "matkhau123", "full_name": "Can bo moi",
        "unit_id": org["ctsv_id"], "position": "Chuyen vien"}, headers=h)
    assert resp.status_code == 200, resp.text
    staff = resp.json()
    assert staff["role"] == "student_affairs"

    resp = client.patch(f"/staff/{staff['id']}", json={"unit_id": org["pdt_id"]}, headers=h)
    assert resp.json()["role"] == "training_office"

    token = login(client, "cb.moi@fams.edu.vn", "matkhau123")
    assert client.get("/faces/pending", headers=auth_headers(token)).status_code == 403


def test_non_admin_cannot_manage_units_or_staff(client, seed, org):
    h = _h(client, "pdt@test.local")
    assert client.post("/units", json={"code": "X", "name": "X", "type": "board"},
                       headers=h).status_code == 403
    assert client.get("/staff", headers=h).status_code == 403
    assert client.get("/units", headers=h).status_code == 200


def test_delete_unit_in_use_returns_409(client, seed, org):
    h = auth_headers(login(client, "admin@test.local", "admin123"))
    assert client.delete(f"/units/{org['cntt_id']}", headers=h).status_code == 409
    new_unit = client.post("/units", json={"code": "B-MOI", "name": "Ban moi", "type": "board"},
                           headers=h).json()
    assert client.delete(f"/units/{new_unit['id']}", headers=h).status_code == 200


def test_invalid_faculty_id_rejected(client, seed, org):
    h = auth_headers(login(client, "admin@test.local", "admin123"))
    resp = client.patch(f"/students/{seed['sv1_id']}", json={"faculty_id": org["pdt_id"]},
                        headers=h)
    assert resp.status_code == 400
