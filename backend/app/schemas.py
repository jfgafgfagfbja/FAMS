from datetime import date, time

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.core.media import SignedMediaUrl
from app.core.timeutil import LocalDateTime
from app.db.models import ROLE_BY_UNIT_TYPE


# ---- Auth ----
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    # App mobile luu refresh_token de lay access token moi qua POST /auth/refresh.
    refresh_token: str | None = None
    expires_in: int | None = None  # so giay access token con hieu luc


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str | None = None


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


class ManagerResetPasswordRequest(BaseModel):
    """Can bo dat lai mat khau cho nguoi khac - khong can mat khau hien tai cua nguoi do."""
    new_password: str

    @field_validator("new_password")
    @classmethod
    def _min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Mat khau moi phai co it nhat 8 ky tu")
        return v


class ChangePasswordRequest(BaseModel):
    """Nguoi dang dang nhap tu doi mat khau - bat buoc nhap dung mat khau hien tai."""
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def _min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Mat khau moi phai co it nhat 8 ky tu")
        return v


# ---- Don vi (Khoa/Phong/Ban) ----
class UnitCreate(BaseModel):
    code: str
    name: str
    type: str  # faculty | training | student_affairs | board

    @field_validator("type")
    @classmethod
    def _valid_type(cls, v: str) -> str:
        if v not in ROLE_BY_UNIT_TYPE:
            raise ValueError("Loai don vi phai la faculty, training, student_affairs hoac board")
        return v


class UnitUpdate(BaseModel):
    code: str | None = None
    name: str | None = None


class UnitOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    type: str


# ---- Can bo phong ban ----
class StaffCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    unit_id: int
    position: str = ""
    # Chi co nghia voi don vi loai Khoa: True = Lanh dao Khoa (Truong/Pho khoa, giam sat +
    # phe duyet), False = Van phong Khoa (giao vu, nhap lieu).
    faculty_leader: bool = False

    @field_validator("password")
    @classmethod
    def _min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Mat khau phai co it nhat 8 ky tu")
        return v


class StaffUpdate(BaseModel):
    full_name: str | None = None
    unit_id: int | None = None
    position: str | None = None
    faculty_leader: bool | None = None


class StaffOut(BaseModel):
    id: int
    user_id: int
    email: str
    full_name: str
    role: str
    unit_id: int
    unit_code: str
    unit_name: str
    unit_type: str
    position: str


# ---- Student ----
class StudentCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    student_code: str
    major: str = ""
    cohort: int = 0
    faculty_id: int | None = None


class StudentUpdate(BaseModel):
    full_name: str | None = None
    major: str | None = None
    cohort: int | None = None
    faculty_id: int | None = None


class StudentOut(BaseModel):
    id: int
    student_code: str
    full_name: str
    major: str
    cohort: int
    # True khi co it nhat 1 anh khuon mat DA DUOC DUYET (dung duoc de nhan dien).
    face_enrolled: bool = False
    face_status: str = "none"  # none | pending | approved | rejected
    consent_given: bool = False
    consent_version: str | None = None
    consent_method: str | None = None       # self | paper
    consent_recorded_by: str | None = None  # email nguoi ghi nhan
    faculty_id: int | None = None
    faculty_name: str | None = None
    email: str | None = None


# ---- Class ----
class ClassCreate(BaseModel):
    class_code: str
    subject_name: str
    lecturer_id: int
    semester: str
    faculty_id: int | None = None


class ClassUpdate(BaseModel):
    class_code: str | None = None
    subject_name: str | None = None
    lecturer_id: int | None = None
    semester: str | None = None
    faculty_id: int | None = None


class ClassOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    class_code: str
    subject_name: str
    lecturer_id: int
    semester: str
    faculty_id: int | None = None
    lecturer_name: str | None = None
    faculty_name: str | None = None
    student_count: int | None = None


# ---- Dia diem diem danh ----
class LocationCreate(BaseModel):
    code: str
    name: str
    latitude: float
    longitude: float
    radius_m: float = 150.0
    is_default: bool = False

    @model_validator(mode="after")
    def _valid_coordinates(self):
        if not -90 <= self.latitude <= 90 or not -180 <= self.longitude <= 180:
            raise ValueError("Toa do khong hop le")
        if not 10 <= self.radius_m <= 5000:
            raise ValueError("Ban kinh phai tu 10 den 5000 m")
        return self


class LocationUpdate(BaseModel):
    code: str | None = None
    name: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    radius_m: float | None = None
    is_default: bool | None = None

    @model_validator(mode="after")
    def _valid_coordinates(self):
        if self.latitude is not None and not -90 <= self.latitude <= 90:
            raise ValueError("Vi do khong hop le")
        if self.longitude is not None and not -180 <= self.longitude <= 180:
            raise ValueError("Kinh do khong hop le")
        if self.radius_m is not None and not 10 <= self.radius_m <= 5000:
            raise ValueError("Ban kinh phai tu 10 den 5000 m")
        return self


class LocationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    latitude: float
    longitude: float
    radius_m: float
    is_default: bool


# ---- Phong hoc ----
def _check_room_geo(obj):
    """Toa do phai di theo cap; ban kinh rieng cua phong bi chan duoi vi sai so GPS."""
    if (obj.latitude is None) != (obj.longitude is None):
        raise ValueError("Phai nhap ca vi do va kinh do, hoac de trong ca hai")
    if obj.latitude is not None and not -90 <= obj.latitude <= 90:
        raise ValueError("Vi do khong hop le")
    if obj.longitude is not None and not -180 <= obj.longitude <= 180:
        raise ValueError("Kinh do khong hop le")
    if obj.radius_m is not None and not 10 <= obj.radius_m <= 5000:
        raise ValueError("Ban kinh phai tu 10 den 5000 m")
    if obj.floor is not None and not -5 <= obj.floor <= 100:
        raise ValueError("Tang khong hop le")
    if obj.capacity is not None and not 1 <= obj.capacity <= 2000:
        raise ValueError("Suc chua phai tu 1 den 2000")
    return obj


class RoomCreate(BaseModel):
    code: str = Field(min_length=1, max_length=30)
    name: str = Field(min_length=1, max_length=255)
    location_id: int
    building: str | None = None
    floor: int | None = None
    capacity: int | None = None
    latitude: float | None = None
    longitude: float | None = None
    radius_m: float | None = None
    is_active: bool = True

    @model_validator(mode="after")
    def _valid(self):
        return _check_room_geo(self)


class RoomUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=30)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    location_id: int | None = None
    building: str | None = None
    floor: int | None = None
    capacity: int | None = None
    latitude: float | None = None
    longitude: float | None = None
    radius_m: float | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def _valid(self):
        return _check_room_geo(self)


class RoomOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    location_id: int
    location_name: str | None = None
    building: str | None = None
    floor: int | None = None
    capacity: int | None = None
    latitude: float | None = None
    longitude: float | None = None
    radius_m: float | None = None
    is_active: bool
    # Ban kinh thuc su duoc ap dung khi doi chieu (da nang len muc san).
    effective_radius_m: float | None = None
    schedule_count: int = 0


def _check_weekday(v: int | None) -> int | None:
    if v is not None and not 0 <= v <= 6:
        raise ValueError("Thu trong tuan phai tu 0 (Thu 2) den 6 (Chu nhat)")
    return v


class ScheduleCreate(BaseModel):
    class_id: int
    weekday: int
    start_time: time
    end_time: time
    # Chon phong tu danh muc (room_id) la cach dung chinh; `room` dang chu chi con de
    # nhap tay cho phong chua kip dua vao danh muc.
    room_id: int | None = None
    room: str | None = None
    location_id: int | None = None

    @field_validator("weekday")
    @classmethod
    def _valid_weekday(cls, v: int | None) -> int | None:
        return _check_weekday(v)

    @model_validator(mode="after")
    def _valid(self):
        if self.start_time >= self.end_time:
            raise ValueError("Gio bat dau phai truoc gio ket thuc")
        if self.room_id is None and not (self.room or "").strip():
            raise ValueError("Phai chon phong hoc hoac nhap ten phong")
        return self


class ScheduleUpdate(BaseModel):
    weekday: int | None = None
    start_time: time | None = None
    end_time: time | None = None
    room_id: int | None = None
    room: str | None = None
    location_id: int | None = None

    @field_validator("weekday")
    @classmethod
    def _valid_weekday(cls, v: int | None) -> int | None:
        return _check_weekday(v)


class ScheduleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    class_id: int
    weekday: int
    start_time: time
    end_time: time
    room: str
    room_id: int | None = None
    room_name: str | None = None
    location_id: int | None = None


# ---- Lecturer ----
class LecturerCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    lecturer_code: str
    department: str = ""
    faculty_id: int | None = None


class LecturerUpdate(BaseModel):
    full_name: str | None = None
    department: str | None = None
    faculty_id: int | None = None


class LecturerOut(BaseModel):
    id: int
    lecturer_code: str
    full_name: str
    department: str
    email: str | None = None
    faculty_id: int | None = None
    faculty_name: str | None = None


# ---- Attendance ----
class SessionCreate(BaseModel):
    schedule_id: int
    session_date: date
    # Bat khi phong co man hinh/may chieu: SV phai quet ma QR dang chieu moi tu diem
    # danh duoc. De trong thi lay mac dinh trong cau hinh he thong.
    require_qr: bool | None = None


class SessionUpdate(BaseModel):
    """Giang vien bat/tat yeu cau quet ma QR ngay trong buoi, khong phai quyet dinh
    tu luc mo phien."""
    require_qr: bool


class CheckinInfoOut(BaseModel):
    """Thong tin toi thieu SV can truoc khi tu diem danh - khong lo danh sach lop
    hay ket qua cua nguoi khac nhu SessionDetail."""
    session_id: int
    require_qr: bool
    room: str


class CheckinCodeOut(BaseModel):
    """Ma diem danh dang hieu luc cua mot phien - giang vien chieu len man hinh."""
    session_id: int
    qr_payload: str
    digits: str
    rotate_seconds: int
    expires_in_seconds: int


class SessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    schedule_id: int
    session_date: date
    status: str


class SessionDetail(BaseModel):
    """Chi tiet 1 phien diem danh, kem thong tin lop/lich de frontend dung
    (vd lay class_id de goi GET /classes/{class_id}/students lam danh sach lop)."""
    id: int
    schedule_id: int
    session_date: date
    status: str
    opened_at: LocalDateTime
    closed_at: LocalDateTime | None = None
    class_id: int
    class_code: str
    subject_name: str
    room: str
    start_time: time
    end_time: time
    lecturer_name: str | None = None
    # Het thoi diem nay (end_time + SESSION_GRACE_MINUTES) khong nhan diem danh nua.
    checkin_deadline: LocalDateTime | None = None
    # Buoi nay co bat buoc quet ma QR trong phong hay khong.
    require_qr: bool = False
    location_name: str | None = None  # dia diem doi chieu GPS khi SV tu diem danh


class RecognizeResult(BaseModel):
    """Ket qua nhan dien 1 khuon mat trong frame."""
    student_id: int | None
    student_code: str | None
    full_name: str | None
    confidence: float
    status: str  # recognized | unknown | already_checked | spoof | confirming
    evidence_image: SignedMediaUrl = None  # URL /evidence/... (co chu ky) lam bang chung
    liveness_score: float | None = None  # diem "mat that" tu anti-spoofing
    bbox: list[int] | None = None  # [x1, y1, x2, y2] de frontend ve overlay
    confirm_count: int | None = None  # so frame da nhan dien trong phien (status=confirming)
    confirm_needed: int | None = None  # so frame can de xac nhan (settings.CONFIRM_FRAMES)


class SelfCheckinResult(BaseModel):
    """Ket qua khi SV tu chup selfie diem danh (chi so khop voi khuon mat cua
    CHINH SV do, khac voi RecognizeResult cua luong camera lop hoc quet nhieu mat)."""
    # recognized | already_checked | not_matched | no_face | multiple_faces | spoof
    # | qr_required | qr_invalid | location_* (xem geo_service)
    status: str
    confidence: float = 0.0
    liveness_score: float | None = None
    evidence_image: SignedMediaUrl = None
    record_id: int | None = None
    record_status: str | None = None  # present | late (khi status=recognized/already_checked)
    message: str = ""
    distance_m: float | None = None       # khoang cach toi dia diem diem danh (neu doi chieu GPS)
    allowed_radius_m: float | None = None


class RecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    checked_at: LocalDateTime
    status: str
    confidence: float
    evidence_image: SignedMediaUrl = ""
    source: str = "camera"
    latitude: float | None = None
    longitude: float | None = None
    location_accuracy: float | None = None
    distance_m: float | None = None


class RecordUpdate(BaseModel):
    """Sua trang thai 1 record sau buoi hoc. Bat buoc co ly do de luu vao AttendanceAudit."""
    status: str  # present | late | absent | excused
    reason: str


class AttendanceAuditOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    record_id: int
    changed_by: int
    old_status: str
    new_status: str
    reason: str
    changed_at: LocalDateTime


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
    evidence_image: SignedMediaUrl = None
    checked_at: LocalDateTime | None = None
    record_id: int | None = None
    source: str | None = None  # camera | selfie | manual
    latitude: float | None = None
    longitude: float | None = None
    location_accuracy: float | None = None
    distance_m: float | None = None


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
    # Phien da mo hom nay cho lich nay (neu co) - FE vao thang phien thay vi mo lai.
    session_id: int | None = None
    session_status: str | None = None


class MyAttendanceSessionOut(BaseModel):
    """1 buoi hoc trong 1 lop, dung khi SV mo rong chi tiet tren trang chuyen can."""
    session_id: int
    session_date: date
    status: str | None = None  # None = SV chua co record cho buoi nay
    checked_at: LocalDateTime | None = None
    confidence: float | None = None
    evidence_image: SignedMediaUrl = None
    record_id: int | None = None
    source: str | None = None  # camera | selfie | manual
    latitude: float | None = None
    longitude: float | None = None
    location_accuracy: float | None = None
    distance_m: float | None = None


class MyClassAttendanceOut(BaseModel):
    """Chuyen can 1 lop hoc phan trong 1 hoc ky cua 1 SV."""
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
    """1 lich hoc kem thong tin lop - dung cho trang quan tri lich hoc toan truong."""
    id: int
    class_id: int
    class_code: str
    subject_name: str
    weekday: int
    start_time: time
    end_time: time
    room: str
    room_id: int | None = None
    location_id: int | None = None
    location_name: str | None = None


class WeekSlotOut(BaseModel):
    """1 o lich trong tuan (ngay cu the), gop san trang thai phien/diem danh cho
    SV hoac GV dang dang nhap - dung cho trang lich tuan, tranh FE goi N+1."""
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
    # Dia diem doi chieu GPS khi SV tu diem danh (rieng cua lich hoc hoac mac dinh cua truong).
    location_name: str | None = None
    location_radius_m: float | None = None


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
    student_id: int | None = None
    student_code: str | None = None
    major: str | None = None
    cohort: int | None = None
    consent_given: bool | None = None
    # Da dong y nhung voi noi dung phien ban cu -> app nhac doc va xac nhan lai.
    consent_outdated: bool | None = None
    face_status: str | None = None
    lecturer_id: int | None = None
    lecturer_code: str | None = None
    department: str | None = None
    faculty_id: int | None = None
    faculty_name: str | None = None
    # Can bo phong ban
    unit_id: int | None = None
    unit_code: str | None = None
    unit_name: str | None = None
    unit_type: str | None = None
    position: str | None = None
    classes: list[MeClassBrief] = []


# ---- Face ----
class EnrollResult(BaseModel):
    ok: bool
    message: str
    num_embeddings: int = 0


class FacePendingOut(BaseModel):
    """1 embedding cho duyet, kem anh doi chieu va canh bao trung (neu co)."""
    id: int
    student_id: int
    student_code: str
    full_name: str
    source_image: SignedMediaUrl = ""
    created_at: LocalDateTime
    duplicate_warning: bool = False
    duplicate_student_code: str | None = None
    duplicate_similarity: float | None = None


class FaceMineOut(BaseModel):
    """Du lieu khuon mat cua chinh SV dang dang nhap (khong tra embedding)."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    reject_reason: str
    created_at: LocalDateTime


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
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: str
    phone: str = ""
    child_count: int = 0


class ParentLinkChild(BaseModel):
    student_code: str


class ParentChildOut(StudentOut):
    """StudentOut mo rong voi danh sach lop hoc phan - dung cho GET /parents/me/children
    de phu huynh co san danh sach hoc ky/lop ma khong phai goi them API khac."""
    classes: list[MeClassBrief] = []


# ---- Thong ke tong hop ----
class OverviewStats(BaseModel):
    classes: int
    students: int
    lecturers: int
    closed_sessions: int
    records: int
    present: int
    late: int
    manual: int
    absent: int
    excused: int
    attendance_rate: float  # (present + late + manual) / records
    absent_rate: float      # absent / records
    warned_students: int    # so SV vuot nguong vang o it nhat 1 lop


class OverviewFacultyRow(OverviewStats):
    faculty_id: int | None
    faculty_code: str | None
    faculty_name: str


class OverviewOut(BaseModel):
    """Thong ke chuyen can tong hop - CHI so lieu, khong ten/anh (dung cho Ban nganh)."""
    scope: str  # school | faculty
    scope_name: str
    semester: str | None
    semesters: list[str]
    totals: OverviewStats
    by_faculty: list[OverviewFacultyRow]


# ---- Thong bao ----
class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kind: str
    title: str
    body: str
    link: str | None = None
    created_at: LocalDateTime
    read_at: LocalDateTime | None = None


class UnreadCountOut(BaseModel):
    count: int


class ParentPreferencesOut(BaseModel):
    notify_email: bool
    notify_present: bool
    # May chu da cau hinh gui email chua - app dung de bao phu huynh khi email chua bat.
    email_available: bool


class ParentPreferencesUpdate(BaseModel):
    notify_email: bool | None = None
    notify_present: bool | None = None


# ---- Nhat ky he thong ----
class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: LocalDateTime
    actor_id: int | None = None
    actor_email: str | None = None
    actor_role: str | None = None
    action: str
    target_type: str | None = None
    target_id: int | None = None
    target_label: str | None = None
    ip: str | None = None
    success: bool
    detail: str | None = None  # JSON {truong: [cu, moi]}


# ---- Dong y sinh trac hoc ----
class ConsentPolicyOut(BaseModel):
    version: str
    title: str
    items: list[str]
    checkbox: str


class ConsentRequest(BaseModel):
    """Phai gui dung phien ban noi dung dang hien hanh: SV dong y voi cai da doc."""
    agreed: bool
    version: str
    method: str = "self"  # self: SV tu bam | paper: SV ky giay, can bo nhap thay
