"""Tao du lieu mau: admin, 1 giang vien, 2 sinh vien, 1 lop, 1 lich hoc.

Chay: python seed.py
"""
from datetime import time

from app.core.security import hash_password
from app.db import models
from app.db.database import SessionLocal, init_db


def seed():
    init_db()
    db = SessionLocal()
    if db.query(models.User).first():
        print("Da co du lieu, bo qua.")
        return

    admin = models.User(email="admin@fams.edu.vn",
                        password_hash=hash_password("admin123"),
                        role="admin", full_name="Quan tri vien")
    gv_user = models.User(email="gv01@fams.edu.vn",
                          password_hash=hash_password("gv123"),
                          role="lecturer", full_name="Nguyen Van Giang")
    db.add_all([admin, gv_user])
    db.flush()

    gv = models.Lecturer(user_id=gv_user.id, lecturer_code="GV01",
                         department="CNTT")
    db.add(gv)
    db.flush()

    students = []
    for i, name in enumerate(["Tran Thi Sinh", "Le Van Vien"], start=1):
        u = models.User(email=f"sv{i:02d}@fams.edu.vn",
                        password_hash=hash_password("sv123"),
                        role="student", full_name=name)
        db.add(u)
        db.flush()
        s = models.Student(user_id=u.id, student_code=f"SV{i:04d}",
                           major="CNTT", cohort=2024)
        db.add(s)
        db.flush()
        students.append(s)

    clazz = models.Class(class_code="INT3306.1", subject_name="Phat trien Web",
                         lecturer_id=gv.id, semester="2026.1")
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
                          role="parent", full_name="Tran Van Phu")
    db.add(ph_user)
    db.flush()
    ph = models.Parent(user_id=ph_user.id, phone="0900000000")
    db.add(ph)
    db.flush()
    db.add(models.ParentStudent(parent_id=ph.id, student_id=students[0].id))

    db.commit()
    print("Seed xong. Tai khoan: admin@fams.edu.vn/admin123, "
          "gv01@fams.edu.vn/gv123, sv01@fams.edu.vn/sv123, ph01@fams.edu.vn/ph123 (phu huynh cua sv01)")


if __name__ == "__main__":
    seed()
