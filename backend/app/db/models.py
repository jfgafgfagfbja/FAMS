from datetime import date, datetime, time

from pgvector.sqlalchemy import Vector
from sqlalchemy import (Date, DateTime, Float, ForeignKey, String, Time,
                        UniqueConstraint, func)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20))  # admin | lecturer | student | parent
    full_name: Mapped[str] = mapped_column(String(255))
    # Moc thoi gian doi mat khau gan nhat - token phat truoc moc nay bi coi la thu
    # hoi (xem core/security.py::get_current_user). Khong the liet ke tung jti da
    # phat truoc do nen dung moc thoi gian de thu hoi hang loat khi reset mat khau.
    credentials_changed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    student: Mapped["Student | None"] = relationship(back_populates="user")
    lecturer: Mapped["Lecturer | None"] = relationship(back_populates="user")


class Student(Base):
    __tablename__ = "students"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    student_code: Mapped[str] = mapped_column(String(20), unique=True)
    major: Mapped[str] = mapped_column(String(100), default="")
    cohort: Mapped[int] = mapped_column(default=0)
    consent_given: Mapped[bool] = mapped_column(default=False)
    consent_given_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped[User] = relationship(back_populates="student")
    embeddings: Mapped[list["FaceEmbedding"]] = relationship(back_populates="student")
    enrollments: Mapped[list["Enrollment"]] = relationship(back_populates="student")


class Lecturer(Base):
    __tablename__ = "lecturers"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    lecturer_code: Mapped[str] = mapped_column(String(20), unique=True)
    department: Mapped[str] = mapped_column(String(100), default="")

    user: Mapped[User] = relationship(back_populates="lecturer")


class Class(Base):
    __tablename__ = "classes"
    id: Mapped[int] = mapped_column(primary_key=True)
    class_code: Mapped[str] = mapped_column(String(30), unique=True)
    subject_name: Mapped[str] = mapped_column(String(255))
    lecturer_id: Mapped[int] = mapped_column(ForeignKey("lecturers.id"))
    semester: Mapped[str] = mapped_column(String(20))  # vd: 2026.1

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
    """Luu vet moi lan giang vien/admin sua trang thai 1 attendance record."""
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
    """Tai khoan phu huynh - admin tao va lien ket thu cong voi (cac) con la SV
    (khong tu dang ky/tu moi qua email, theo dung quy trinh admin quan ly nguoi
    dung hien co cua he thong)."""
    __tablename__ = "parents"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    phone: Mapped[str] = mapped_column(String(20), default="")

    user: Mapped[User] = relationship()
    children: Mapped[list["ParentStudent"]] = relationship(back_populates="parent")


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
