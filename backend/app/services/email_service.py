"""Email Service — gui email qua SMTP (ma OTP dat lai mat khau, thong bao cho phu huynh).

Neu chua cau hinh SMTP_HOST (rong, mac dinh khi dev): khong gui email that, chi
log OTP ra console kem canh bao "DEV MODE" de dev/test luong quen mat khau ma
khong can may chu SMTP that.

Gmail: SMTP_HOST=smtp.gmail.com, SMTP_PORT=587, SMTP_USER = dia chi Gmail, SMTP_PASSWORD
= "mat khau ung dung" 16 ky tu (KHONG phai mat khau Gmail - phai bat xac minh 2 buoc moi
tao duoc), MAIL_FROM = chinh dia chi Gmail do (Gmail tu thay From neu khac).
"""
import logging
import smtplib
from contextlib import contextmanager
from email.message import EmailMessage
from email.utils import formataddr

from app.core.config import settings

logger = logging.getLogger(__name__)

# Gmail treo ket noi thi cung khong de tac vu nen dung mai.
SMTP_TIMEOUT_SECONDS = 30


def is_configured() -> bool:
    return bool(settings.SMTP_HOST)


def build_message(to_email: str, subject: str, text: str) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = formataddr(("FAMS", settings.MAIL_FROM))
    msg["To"] = to_email
    msg.set_content(text)
    return msg


@contextmanager
def smtp_connection():
    """Mot ket noi SMTP da dang nhap, dung de gui ca lo thu. Gmail de chan neu moi thu
    lai dang nhap mot lan."""
    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=SMTP_TIMEOUT_SECONDS) as server:
        server.starttls()
        if settings.SMTP_USER:
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        yield server


def send_otp_email(to_email: str, otp: str) -> None:
    if not is_configured():
        logger.warning(
            "[DEV MODE] Chua cau hinh SMTP_HOST nen khong gui email that. "
            "Ma OTP dat lai mat khau cho %s la: %s (het han sau %s phut).",
            to_email, otp, settings.OTP_EXPIRE_MINUTES,
        )
        return

    msg = build_message(
        to_email, "Mã OTP đặt lại mật khẩu FAMS",
        f"Mã OTP đặt lại mật khẩu của bạn là: {otp}\n"
        f"Mã có hiệu lực trong {settings.OTP_EXPIRE_MINUTES} phút và chỉ dùng được 1 lần.\n\n"
        "Nếu bạn không yêu cầu đặt lại mật khẩu, vui lòng bỏ qua email này.",
    )
    with smtp_connection() as server:
        server.send_message(msg)
