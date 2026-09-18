"""Tao du lieu mau: admin, giang vien, sinh vien, phu huynh, lop, lich hoc va cac don vi
(Khoa, Phong Dao tao, Phong CTSV, Ban nganh) kem tai khoan can bo.

Chay: python seed.py
- DB trong: tao toan bo du lieu mau.
- DB da co du lieu: chi bo sung don vi + tai khoan can bo con thieu (khong dung du lieu cu).
"""
from datetime import time

from app.core.security import hash_password
from app.db import models
from app.db.database import SessionLocal, init_db

UNITS = [
    ("K-CNTT", "Khoa Cong nghe thong tin", models.UNIT_FACULTY),
    ("K-KT", "Khoa Kien truc", models.UNIT_FACULTY),
    ("P-DT", "Phong Dao tao", models.UNIT_TRAINING),
    ("P-CTSV", "Phong Cong tac sinh vien", models.UNIT_AFFAIRS),
    ("B-TTPC", "Ban Thanh tra - Phap che", models.UNIT_BOARD),
]

# Dia diem diem danh: (ma, ten, vi do, kinh do, ban kinh m). Toa do GAN DUNG cua co so
# 566 Nui Thanh - can cap nhat bang nut "Lay vi tri hien tai" tai truong truoc khi dung that.
LOCATIONS = [
    ("CS-NUITHANH", "Co so chinh - 566 Nui Thanh", 16.0322, 108.2213, 200.0),
]

# email, mat khau, ho ten, ma don vi, chuc vu
STAFF = [
    ("pdt01@fams.edu.vn", "pdt12345", "Le Thi Dao Tao", "P-DT", "Chuyen vien"),
    ("ctsv01@fams.edu.vn", "ctsv1234", "Pham Van Cong Tac", "P-CTSV", "Chuyen vien"),
    ("khoa.cntt@fams.edu.vn", "khoa1234", "Nguyen Thi Giao Vu", "K-CNTT", "Giao vu Khoa"),
    ("ban01@fams.edu.vn", "ban12345", "Hoang Van Thanh Tra", "B-TTPC", "Truong ban"),
]


def seed_units_and_staff(db) -> list[str]:
    """Bo sung don vi + tai khoan can bo neu chua co. Tra ve danh sach tai khoan vua tao."""
    units = {}
    for code, name, unit_type in UNITS:
        unit = db.query(models.Unit).filter_by(code=code).first()
        if not unit:
            unit = models.Unit(code=code, name=name, type=unit_type)
            db.add(unit)
            db.flush()
        units[code] = unit

    created = []
    for email, password, full_name, unit_code, position in STAFF:
        if db.query(models.User).filter_by(email=email).first():
            continue
        unit = units[unit_code]
        user = models.User(email=email, password_hash=hash_password(password),
                           role=models.ROLE_BY_UNIT_TYPE[unit.type], full_name=full_name)
        db.add(user)
        db.flush()
        db.add(models.Staff(user_id=user.id, unit_id=unit.id, position=position))
        created.append(f"{email}/{password}")
    db.commit()
    return created


def seed_locations(db, make_default: bool) -> None:
    """Tao dia diem mau neu chua co. make_default=False voi DB da co du lieu: khong tu bat
    doi chieu GPS cho cac lich hoc dang chay khi toa do chua duoc kiem tra tai truong."""
    for code, name, lat, lng, radius in LOCATIONS:
        if not db.query(models.Location).filter_by(code=code).first():
            db.add(models.Location(code=code, name=name, latitude=lat, longitude=lng,
                                   radius_m=radius, is_default=make_default))
    db.commit()


def seed():
    init_db()
    db = SessionLocal()
    try:
        if db.query(models.User).first():
            created = seed_units_and_staff(db)
            seed_locations(db, make_default=False)
            print("Da co du lieu, chi bo sung don vi/can bo."
                  + (f" Tai khoan moi: {', '.join(created)}" if created else ""))
            return

        created_staff = seed_units_and_staff(db)
        seed_locations(db, make_default=True)
        cntt = db.query(models.Unit).filter_by(code="K-CNTT").first()

        admin = models.User(email="admin@fams.edu.vn",
                            password_hash=hash_password("admin123"),
                            role=models.ROLE_ADMIN, full_name="Quan tri vien")
        gv_user = models.User(email="gv01@fams.edu.vn",
                              password_hash=hash_password("gv123"),
                              role=models.ROLE_LECTURER, full_name="Nguyen Van Giang")
        db.add_all([admin, gv_user])
        db.flush()

        gv = models.Lecturer(user_id=gv_user.id, lecturer_code="GV01",
                             department="CNTT", faculty_id=cntt.id)
        db.add(gv)
        db.flush()

        students = []
        for i, name in enumerate(["Tran Thi Sinh", "Le Van Vien"], start=1):
            u = models.User(email=f"sv{i:02d}@fams.edu.vn",
                            password_hash=hash_password("sv123"),
                            role=models.ROLE_STUDENT, full_name=name)
            db.add(u)
            db.flush()
            s = models.Student(user_id=u.id, student_code=f"SV{i:04d}",
                               major="CNTT", cohort=2024, faculty_id=cntt.id)
            db.add(s)
            db.flush()
            students.append(s)

        clazz = models.Class(class_code="INT3306.1", subject_name="Phat trien Web",
                             lecturer_id=gv.id, semester="2026.1", faculty_id=cntt.id)
        db.add(clazz)
        db.flush()

        for s in students:
            db.add(models.Enrollment(student_id=s.id, class_id=clazz.id))

        db.add(models.Schedule(class_id=clazz.id, weekday=0,
                               start_time=time(7, 0), end_time=time(9, 0),
                               room="P101"))
        db.flush()

        ph_user = models.User(email="ph01@fams.edu.vn",
                              password_hash=hash_password("ph123"),
                              role=models.ROLE_PARENT, full_name="Tran Van Phu")
        db.add(ph_user)
        db.flush()
        ph = models.Parent(user_id=ph_user.id, phone="0900000000")
        db.add(ph)
        db.flush()
        db.add(models.ParentStudent(parent_id=ph.id, student_id=students[0].id))

        db.commit()
        print("Seed xong. Tai khoan: admin@fams.edu.vn/admin123, "
              "gv01@fams.edu.vn/gv123, sv01@fams.edu.vn/sv123, ph01@fams.edu.vn/ph123 "
              f"(phu huynh cua sv01), can bo: {', '.join(created_staff)}")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
