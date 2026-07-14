from datetime import date, datetime, time

from pydantic import BaseModel, EmailStr


# ---- Auth ----
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str


# ---- Student ----
class StudentCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    student_code: str
    major: str = ""
    cohort: int = 0


class StudentUpdate(BaseModel):
    full_name: str | None = None
    major: str | None = None
    cohort: int | None = None


class StudentOut(BaseModel):
    id: int
    student_code: str
    full_name: str
    major: str
    cohort: int
    face_enrolled: bool = False
    consent_given: bool = False

    class Config:
        from_attributes = True


# ---- Class ----
class ClassCreate(BaseModel):
    class_code: str
    subject_name: str
    lecturer_id: int
    semester: str


class ClassUpdate(BaseModel):
    class_code: str | None = None
    subject_name: str | None = None
    lecturer_id: int | None = None
    semester: str | None = None


class ClassOut(BaseModel):
    id: int
    class_code: str
    subject_name: str
    lecturer_id: int
    semester: str

    class Config:
        from_attributes = True


class ScheduleCreate(BaseModel):
    class_id: int
    weekday: int
    start_time: time
    end_time: time
    room: str


# ---- Attendance ----
class SessionCreate(BaseModel):
    schedule_id: int
    session_date: date


class SessionOut(BaseModel):
    id: int
    schedule_id: int
    session_date: date
    status: str

    class Config:
        from_attributes = True


class RecognizeResult(BaseModel):
    """Ket qua nhan dien 1 khuon mat trong frame."""
    student_id: int | None
    student_code: str | None
    full_name: str | None
    confidence: float
    status: str  # recognized | unknown | already_checked
    evidence_image: str | None = None  # URL /evidence/... lam bang chung


class RecordOut(BaseModel):
    id: int
    student_id: int
    checked_at: datetime
    status: str
    confidence: float
    evidence_image: str = ""

    class Config:
        from_attributes = True


class ManualCheck(BaseModel):
    student_id: int


# ---- Face ----
class EnrollResult(BaseModel):
    ok: bool
    message: str
    num_embeddings: int = 0
