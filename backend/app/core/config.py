from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://fams:fams123@localhost:5432/fams"
    SECRET_KEY: str = "change-me"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30   # app mobile dung refresh token de khong bi dang xuat lien tuc
    RECOGNITION_THRESHOLD: float = 0.45   # nguong cosine de nhan dien
    DUPLICATE_THRESHOLD: float = 0.60     # nguong canh bao trung khi enrollment
    LATE_AFTER_MINUTES: int = 15          # sau X phut tinh la muon
    EARLY_OPEN_MINUTES: int = 15          # duoc mo phien som X phut truoc gio bat dau tiet
    # Sau gio ket thuc tiet X phut: khong nhan diem danh nua va phien dang mo tu dong
    # dong (sinh ban ghi vang) - tranh phien bi quen dong ton tai mai.
    SESSION_GRACE_MINUTES: int = 30
    EVIDENCE_DIR: str = "./evidence"
    EVIDENCE_RETENTION_DAYS: int = 90     # anh bang chung qua han bi xoa tu dong
    # Anh bang chung/anh dang ky khuon mat chi truy cap duoc qua URL co chu ky HMAC
    # (api tra ve kem ?exp=&sig=), het han sau X phut.
    MEDIA_URL_EXPIRE_MINUTES: int = 60
    CORS_ORIGINS: str = "http://localhost:5173"  # phan cach boi dau phay
    ANTISPOOF_ENABLED: bool = True        # bat/tat kiem tra liveness (tat khi may dev yeu)
    ANTISPOOF_THRESHOLD: float = 0.5      # diem "that" toi thieu de coi la mat that
    ANTISPOOF_MODEL_PATH: str = "./models/2.7_80x80_MiniFASNetV2.onnx"
    CONFIRM_FRAMES: int = 2                # so frame can nhan dien du de ghi attendance record
    # SV tu diem danh (selfie) phai o trong ban kinh dia diem cua lich hoc (hoac dia diem mac
    # dinh). Chua cau hinh dia diem nao -> bo qua doi chieu. GPS do app gui len nen van co the bi
    # gia mao - day la lop kiem tra bo sung, khong thay the xac nhan cua giang vien.
    SELF_CHECKIN_REQUIRE_LOCATION: bool = True
    SELF_CHECKIN_MAX_ACCURACY_M: float = 100.0  # sai so GPS lon hon muc nay -> yeu cau thu lai
    # Muc san cho ban kinh khi doi chieu theo toa do rieng cua phong. GPS trong nha sai so
    # hang chuc met, dat thap hon muc nay se chan oan sinh vien dang ngoi dung lop.
    ROOM_MIN_RADIUS_M: float = 50.0
    # Ma QR diem danh doi sau bao nhieu giay. Ngan thi anh chup man hinh nhanh het han,
    # nhung SV quet cham de truot; 30 giay la muc can bang (chap nhan ca o lien truoc
    # nen thuc te con tu 30 den 60 giay de quet).
    CHECKIN_QR_ROTATE_SECONDS: int = 30
    # Mac dinh cho o "yeu cau quet ma QR" khi giang vien mo phien diem danh.
    SELF_CHECKIN_REQUIRE_QR_DEFAULT: bool = False
    # Dia chi cong khai cua giao dien web, dung de gan duong link "xem chi tiet" vao email
    # gui phu huynh (vd https://fams.tail313000.ts.net). De trong thi email khong kem link.
    APP_PUBLIC_URL: str = ""
    # Tac vu nen gui email thong bao: bao lau quet hang doi mot lan, va thu toi da may lan
    # cho moi thu truoc khi danh dau that bai.
    NOTIFY_EMAIL_INTERVAL_SECONDS: int = 15
    NOTIFY_EMAIL_MAX_ATTEMPTS: int = 3
    ABSENCE_WARN_RATIO: float = 0.2        # ti le vang (khong tinh excused) -> canh bao cam thi

    # Mui gio cua moi gia tri datetime luu trong DB (naive, gio dia phuong) - dung de
    # tra ve ISO 8601 kem offset cho client (Flutter/React parse dung gio).
    APP_UTC_OFFSET_MINUTES: int = 420

    # Chong do mat khau: gioi han theo IP (sau nginx can uvicorn --proxy-headers) va
    # theo tai khoan (nhieu SV dung chung 1 IP wifi truong/4G nen khong the chi dua vao IP).
    LOGIN_RATE_LIMIT: str = "30/minute"
    LOGIN_MAX_FAILED_PER_ACCOUNT: int = 5
    LOGIN_FAILED_WINDOW_MINUTES: int = 5

    # Tat vong lap nen (don anh, tu dong dong phien) - test dat False de khong dung toi DB that.
    BACKGROUND_JOBS_ENABLED: bool = True

    # Quen mat khau (OTP qua email) - SMTP_HOST rong = chua cau hinh, email_service
    # se chi log OTP ra console kem canh bao "DEV MODE" thay vi gui that.
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    MAIL_FROM: str = "no-reply@fams.edu.vn"
    OTP_EXPIRE_MINUTES: int = 10

    class Config:
        env_file = ".env"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()
