from datetime import date, datetime, time

from pgvector.sqlalchemy import Vector
from sqlalchemy import (Date, DateTime, Float, ForeignKey, String, Time,
                        UniqueConstraint, func)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

# Vai tro nguoi dung. Nhom phong ban (TRAINING/AFFAIRS/FACULTY/BOARD) gan voi 1 don vi
# qua bang staff - quyen cu the xem core/authz.py.
ROLE_ADMIN = "admin"
ROLE_LECTURER = "lecturer"
ROLE_STUDENT = "student"
ROLE_PARENT = "parent"
ROLE_TRAINING = "training_office"    # Phong Dao tao
ROLE_AFFAIRS = "student_affairs"     # Phong Cong tac sinh vien
ROLE_FACULTY = "faculty_office"      # Van phong/giao vu Khoa
ROLE_BOARD = "board"                 # Ban nganh khac (chi xem thong ke tong hop)
STAFF_ROLES = (ROLE_TRAINING, ROLE_AFFAIRS, ROLE_FACULTY, ROLE_BOARD)

# Loai don vi -> vai tro cua can bo thuoc don vi do.
UNIT_FACULTY = "faculty"
UNIT_TRAINING = "training"
UNIT_AFFAIRS = "student_affairs"
UNIT_BOARD = "board"
ROLE_BY_UNIT_TYPE = {
    UNIT_FACULTY: ROLE_FACULTY,
    UNIT_TRAINING: ROLE_TRAINING,
    UNIT_AFFAIRS: ROLE_AFFAIRS,
    UNIT_BOARD: ROLE_BOARD,
}


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    # admin | lecturer | student | parent | training_office | student_affairs | faculty_office | board
    role: Mapped[str] = mapped_column(String(20))
    full_name: Mapped[str] = mapped_column(String(255))
    # Moc thoi gian doi mat khau gan nhat (thong tin doi soat; viec thu hoi token dung
    # token_version ben duoi).
    credentials_changed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # Tang len moi lan dat lai mat khau; access token mang claim "tv" - lech version la
    # token cu, bi tu choi ngay (khong phu thuoc do phan giai giay cua "iat").
    token_version: Mapped[int] = mapped_column(default=0, server_default="0")

    student: Mapped["Student | None"] = relationship(back_populates="user")
    lecturer: Mapped["Lecturer | None"] = relationship(back_populates="user")


class Unit(Base):
    """Don vi trong truong: Khoa, Phong Dao tao, Phong Cong tac SV, Ban nganh."""
    __tablename__ = "units"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    type: Mapped[str] = mapped_column(String(20))  # faculty | training | student_affairs | board


class Staff(Base):
    """Ho so can bo phong ban - 1 user thuoc dung 1 don vi, vai tro suy ra tu loai don vi."""
    __tablename__ = "staff"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    unit_id: Mapped[int] = mapped_column(ForeignKey("units.id"))
    position: Mapped[str] = mapped_column(String(100), default="")

    user: Mapped[User] = relationship()
    unit: Mapped[Unit] = relationship()


class Student(Base):
    __tablename__ = "students"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    student_code: Mapped[str] = mapped_column(String(20), unique=True)
    major: Mapped[str] = mapped_column(String(100), default="")
    cohort: Mapped[int] = mapped_column(default=0)
    faculty_id: Mapped[int | None] = mapped_column(ForeignKey("units.id"), nullable=True)
    consent_given: Mapped[bool] = mapped_column(default=False)
    consent_given_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped[User] = relationship(back_populates="student")
    faculty: Mapped[Unit | None] = relationship()
    embeddings: Mapped[list["FaceEmbedding"]] = relationship(back_populates="student")
    enrollments: Mapped[list["Enrollment"]] = relationship(back_populates="student")


class Lecturer(Base):
    __tablename__ = "lecturers"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    lecturer_code: Mapped[str] = mapped_column(String(20), unique=True)
    department: Mapped[str] = mapped_column(String(100), default="")
    faculty_id: Mapped[int | None] = mapped_column(ForeignKey("units.id"), nullable=True)

    user: Mapped[User] = relationship(back_populates="lecturer")
    faculty: Mapped[Unit | None] = relationship()


class Class(Base):
    __tablename__ = "classes"
    id: Mapped[int] = mapped_column(primary_key=True)
    class_code: Mapped[str] = mapped_column(String(30), unique=True)
    subject_name: Mapped[str] = mapped_column(String(255))
    lecturer_id: Mapped[int] = mapped_column(ForeignKey("lecturers.id"))
    semester: Mapped[str] = mapped_column(String(20))  # vd: 2026.1
    # Khoa quan ly hoc phan - quyet dinh pham vi xem cua can bo Khoa.
    faculty_id: Mapped[int | None] = mapped_column(ForeignKey("units.id"), nullable=True)

    lecturer: Mapped[Lecturer] = relationship()
    faculty: Mapped[Unit | None] = relationship()
    enrollments: Mapped[list["Enrollment"]] = relationship(back_populates="clazz")
    schedules: Mapped[list["Schedule"]] = relationship(back_populates="clazz")


class Enrollment(Base):
    __tablename__ = "enrollments"
    __table_args__ = (UniqueConstraint("student_id", "class_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"))
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id"))

    student: Mapped[Student] = relationship(back_populates="enrollments")
    clazz: Mapped[Class] = relationship(back_populates="enrollments")


class Schedule(Base):
    __tablename__ = "schedules"
    id: Mapped[int] = mapped_column(primary_key=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id"))
    weekday: Mapped[int] = mapped_column()  # 0 = thu 2
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)
    room: Mapped[str] = mapped_column(String(50))

    clazz: Mapped[Class] = relationship(back_populates="schedules")


class AttendanceSession(Base):
    __tablename__ = "attendance_sessions"
    # Moi lich hoc chi co toi da 1 phien diem danh trong 1 ngay - chan mo trung
    # o tang DB (open_session cung kiem tra truoc de tra 400 de hieu).
    __table_args__ = (UniqueConstraint("schedule_id", "session_date"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    schedule_id: Mapped[int] = mapped_column(ForeignKey("schedules.id"))
    session_date: Mapped[date] = mapped_column(Date)
    opened_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(10), default="open")  # open | closed

    schedule: Mapped[Schedule] = relationship()
    records: Mapped[list["AttendanceRecord"]] = relationship(back_populates="session")


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"
    __table_args__ = (UniqueConstraint("session_id", "student_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("attendance_sessions.id"))
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"))
    checked_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    status: Mapped[str] = mapped_column(String(10))  # present | late | absent | manual | excused
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    evidence_image: Mapped[str] = mapped_column(String(500), default="")
    # Nguon tao record: camera (GV quet ca lop), selfie (SV tu chup + GPS trinh
    # duyet), manual (GV xac nhan tay). latitude/longitude/location_accuracy chi
    # co gia tri khi source="selfie".
    source: Mapped[str] = mapped_column(String(10), default="camera")
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    location_accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)

    session: Mapped[AttendanceSession] = relationship(back_populates="records")
    student: Mapped[Student] = relationship()


class AttendanceAudit(Base):
    """Luu vet moi lan giang vien/admin/phong ban sua trang thai 1 attendance record."""
    __tablename__ = "attendance_audits"
    id: Mapped[int] = mapped_column(primary_key=True)
    record_id: Mapped[int] = mapped_column(ForeignKey("attendance_records.id"))
    changed_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    old_status: Mapped[str] = mapped_column(String(10))
    new_status: Mapped[str] = mapped_column(String(10))
    reason: Mapped[str] = mapped_column(String(500))
    changed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    record: Mapped[AttendanceRecord] = relationship()
    user: Mapped[User] = relationship()


class FaceEmbedding(Base):
    __tablename__ = "face_embeddings"
    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"))
    embedding: Mapped[list[float]] = mapped_column(Vector(512))
    # Anh khuon mat (da cat) luu TAM de can bo doi chieu khi duyet - xoa ngay khi
    # duyet/tu choi (xem api/faces.py), dung voi dieu khoan dong y cua SV.
    source_image: Mapped[str] = mapped_column(String(500), default="")
    status: Mapped[str] = mapped_column(String(10), default="pending")  # pending | approved | rejected
    reject_reason: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    student: Mapped[Student] = relationship(back_populates="embeddings")


class RevokedToken(Base):
    """JWT da bi thu hoi (logout truoc han). Kiem tra jti moi lan xac thuc."""
    __tablename__ = "revoked_tokens"
    id: Mapped[int] = mapped_column(primary_key=True)
    jti: Mapped[str] = mapped_column(String(36), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)


class RefreshToken(Base):
    """Refresh token (app mobile). Chi luu SHA-256 cua token; moi lan /auth/refresh xoay
    vong sang token moi, token cu bi thu hoi. Dung lai token da thu hoi = nghi bi danh
    cap -> thu hoi toan bo refresh token cua user."""
    __tablename__ = "refresh_tokens"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)  # UTC
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)  # UTC

    user: Mapped[User] = relationship()


class PasswordReset(Base):
    """Yeu cau dat lai mat khau qua OTP gui email. Khong luu OTP tho, chi luu ban bam."""
    __tablename__ = "password_resets"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    otp_hash: Mapped[str] = mapped_column(String(255))
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    used: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped[User] = relationship()


class Parent(Base):
    """Tai khoan phu huynh - admin/P.CTSV tao va lien ket thu cong voi (cac) con la SV
    (khong tu dang ky/tu moi qua email, theo dung quy trinh quan ly nguoi dung hien co)."""
    __tablename__ = "parents"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    phone: Mapped[str] = mapped_column(String(20), default="")

    user: Mapped[User] = relationship()
    children: Mapped[list["ParentStudent"]] = relationship(
        back_populates="parent", cascade="all, delete-orphan")


class ParentStudent(Base):
    """Lien ket phu huynh <-> sinh vien. 1 phu huynh co the theo doi nhieu con,
    1 SV co the duoc nhieu phu huynh theo doi (vd ca cha lan me)."""
    __tablename__ = "parent_students"
    __table_args__ = (UniqueConstraint("parent_id", "student_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    parent_id: Mapped[int] = mapped_column(ForeignKey("parents.id"))
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"))

    parent: Mapped[Parent] = relationship(back_populates="children")
    student: Mapped[Student] = relationship()
