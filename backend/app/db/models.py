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
    role: Mapped[str] = mapped_column(String(20))  # admin | lecturer | student
    full_name: Mapped[str] = mapped_column(String(255))

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
