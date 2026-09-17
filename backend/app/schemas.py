from datetime import date, datetime, time

from pydantic import BaseModel, EmailStr, field_validator


# ---- Auth ----
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str


class ForgotPasswordRequest(BaseModel):
    # str thuong, khong dung EmailStr: day la tra cuu email DA TON TAI (giong
    # OAuth2PasswordRequestForm.username o /auth/login), khong phai tao moi, nen
    # khong can/khong nen ep dinh dang - email khong hop le don gian se khong
    # khop user nao va van nhan thong bao chung nhu binh thuong.
    email: str


class ResetPasswordRequest(BaseModel):
    email: str
    otp: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def _min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Mat khau moi phai co it nhat 8 ky tu")
        return v


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


class ScheduleUpdate(BaseModel):
    weekday: int | None = None
    start_time: time | None = None
    end_time: time | None = None
    room: str | None = None


class ScheduleOut(BaseModel):
    id: int
    class_id: int
    weekday: int
    start_time: time
    end_time: time
    room: str

    class Config:
        from_attributes = True


# ---- Lecturer ----
class LecturerCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    lecturer_code: str
    department: str = ""


class LecturerUpdate(BaseModel):
    full_name: str | None = None
    department: str | None = None


class LecturerOut(BaseModel):
    id: int
    lecturer_code: str
    full_name: str
    department: str

    class Config:
        from_attributes = True


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


class SessionDetail(BaseModel):
    """Chi tiet 1 phien diem danh, kem thong tin lop/lich de frontend dung
    (vd lay class_id de goi GET /classes/{class_id}/students lam danh sach lop)."""
    id: int
    schedule_id: int
    session_date: date
    status: str
    opened_at: datetime
    class_id: int
    class_code: str
    subject_name: str
    room: str
    start_time: time
    end_time: time


class RecognizeResult(BaseModel):
    """Ket qua nhan dien 1 khuon mat trong frame."""
    student_id: int | None
    student_code: str | None
    full_name: str | None
    confidence: float
    status: str  # recognized | unknown | already_checked | spoof | confirming
    evidence_image: str | None = None  # URL /evidence/... lam bang chung
    liveness_score: float | None = None  # diem "mat that" tu anti-spoofing
    bbox: list[int] | None = None  # [x1, y1, x2, y2] de frontend ve overlay
    confirm_count: int | None = None  # so frame da nhan dien trong phien (status=confirming)
    confirm_needed: int | None = None  # so frame can de xac nhan (settings.CONFIRM_FRAMES)


class SelfCheckinResult(BaseModel):
    """Ket qua khi SV tu chup selfie diem danh (chi so khop voi khuon mat cua
    CHINH SV do, khac voi RecognizeResult cua luong camera lop hoc quet nhieu mat)."""
    status: str  # recognized | already_checked | not_matched | no_face | multiple_faces | spoof
    confidence: float = 0.0
    liveness_score: float | None = None
    evidence_image: str | None = None
    record_id: int | None = None
    record_status: str | None = None  # present | late (khi status=recognized/already_checked)
    message: str = ""


class RecordOut(BaseModel):
    id: int
    student_id: int
    checked_at: datetime
    status: str
    confidence: float
    evidence_image: str = ""
    source: str = "camera"
    latitude: float | None = None
    longitude: float | None = None
    location_accuracy: float | None = None

    class Config:
        from_attributes = True


class RecordUpdate(BaseModel):
    """Sua trang thai 1 record sau buoi hoc. Bat buoc co ly do de luu vao AttendanceAudit."""
    status: str  # present | late | absent | excused
    reason: str


class AttendanceAuditOut(BaseModel):
    id: int
    record_id: int
    changed_by: int
    old_status: str
    new_status: str
    reason: str
    changed_at: datetime

    class Config:
        from_attributes = True


class ManualCheck(BaseModel):
    student_id: int


class RosterEntryOut(BaseModel):
    """1 dong trong danh sach lop gop voi trang thai diem danh cua 1 phien cu the -
    tranh FE phai goi rieng danh sach lop + danh sach record roi tu ghep (N+1)."""
    student_id: int
    student_code: str
    full_name: str
    status: str | None = None  # None = chua diem danh
    confidence: float | None = None
    evidence_image: str | None = None
    checked_at: datetime | None = None
    record_id: int | None = None
    source: str | None = None  # camera | selfie | manual
    latitude: float | None = None
    longitude: float | None = None
    location_accuracy: float | None = None


class TodayScheduleOut(BaseModel):
    """1 tiet hoc hom nay cua giang vien dang dang nhap."""
    schedule_id: int
    class_id: int
    class_code: str
    subject_name: str
    weekday: int
    start_time: time
    end_time: time
    room: str
    # Gio som nhat duoc mo phien (= start_time - EARLY_OPEN_MINUTES), tinh san o
    # backend de FE khong phai hardcode nguong cau hinh.
    open_from: time


class MyAttendanceSessionOut(BaseModel):
    """1 buoi hoc trong 1 lop, dung khi SV mo rong chi tiet tren trang chuyen can."""
    session_id: int
    session_date: date
    status: str | None = None  # None = SV chua co record cho buoi nay
    checked_at: datetime | None = None
    confidence: float | None = None
    evidence_image: str | None = None
    record_id: int | None = None
    source: str | None = None  # camera | selfie | manual
    latitude: float | None = None
    longitude: float | None = None
    location_accuracy: float | None = None


class MyClassAttendanceOut(BaseModel):
    """Chuyen can 1 lop hoc phan trong 1 hoc ky cua chinh SV dang dang nhap."""
    class_id: int
    class_code: str
    subject_name: str
    semester: str
    lecturer_name: str
    lecturer_email: str
    present: int
    late: int
    absent: int
    excused: int
    manual: int
    total_sessions: int
    absent_ratio: float
    warn_ratio: float  # settings.ABSENCE_WARN_RATIO - de FE tinh nguong "sap cam thi" ma khong hardcode
    warning: bool
    sessions: list[MyAttendanceSessionOut]


class ScheduleWithClassOut(BaseModel):
    """1 lich hoc kem thong tin lop - dung cho trang quan tri /admin/schedules
    (xem toan bo lich hoc cua truong, khong chi 1 lop)."""
    id: int
    class_id: int
    class_code: str
    subject_name: str
    weekday: int
    start_time: time
    end_time: time
    room: str


class WeekSlotOut(BaseModel):
    """1 o lich trong tuan (ngay cu the), gop san trang thai phien/diem danh cho
    SV hoac GV dang dang nhap - dung cho trang /schedule, tranh FE goi N+1."""
    date: date
    weekday: int
    schedule_id: int
    class_id: int
    class_code: str
    subject_name: str
    room: str
    start_time: time
    end_time: time
    session_id: int | None = None
    session_status: str | None = None  # None (chua mo phien) | open | closed
    # Gio som nhat duoc mo phien (= start_time - EARLY_OPEN_MINUTES) - GV dung de
    # biet nut "Mo phien" hop le tu luc nao ma khong phai hardcode nguong o FE.
    open_from: time | None = None
    my_status: str | None = None  # SV: trang thai diem danh cua chinh minh (neu co)
    present_count: int | None = None  # GV: so SV co mat khi phien da dong
    total_count: int | None = None  # GV: tong so SV ghi danh lop


# ---- Me ----
class MeClassBrief(BaseModel):
    """Thong tin rut gon 1 lop, dung trong GET /me de frontend lay lich hoc/day."""
    id: int
    class_code: str
    subject_name: str
    semester: str


class MeOut(BaseModel):
    """Thong tin tai khoan dang dang nhap, kem ho so va danh sach lop lien quan."""
    id: int
    email: str
    full_name: str
    role: str
    student_code: str | None = None
    major: str | None = None
    cohort: int | None = None
    consent_given: bool | None = None
    lecturer_code: str | None = None
    department: str | None = None
    classes: list[MeClassBrief] = []


# ---- Face ----
class EnrollResult(BaseModel):
    ok: bool
    message: str
    num_embeddings: int = 0


class FacePendingOut(BaseModel):
    """1 embedding cho duyet, kem canh bao trung (neu co) de admin thay khi duyet."""
    id: int
    student_id: int
    student_code: str
    full_name: str
    source_image: str
    created_at: datetime
    duplicate_warning: bool = False
    duplicate_student_code: str | None = None
    duplicate_similarity: float | None = None


class FaceRejectBody(BaseModel):
    reason: str
# ---- Parent ----
class ParentCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    phone: str = ""


class ParentUpdate(BaseModel):
    full_name: str | None = None
    phone: str | None = None


class ParentOut(BaseModel):
    id: int
    full_name: str
    email: str
    phone: str = ""
    child_count: int = 0

    class Config:
        from_attributes = True


class ParentLinkChild(BaseModel):
    student_code: str


class ParentChildOut(StudentOut):
    """StudentOut mo rong voi danh sach lop hoc phan - dung cho GET /parents/me/children
    de phu huynh co san danh sach hoc ky/lop ma khong phai goi them API khac."""
    classes: list[MeClassBrief] = []
