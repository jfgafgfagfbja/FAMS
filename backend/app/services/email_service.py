"""Email Service — gui ma OTP dat lai mat khau qua SMTP.

Neu chua cau hinh SMTP_HOST (rong, mac dinh khi dev): khong gui email that, chi
log OTP ra console kem canh bao "DEV MODE" de dev/test luong quen mat khau ma
khong can may chu SMTP that.
"""
import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings

logger = logging.getLogger(__name__)


def send_otp_email(to_email: str, otp: str) -> None:
    if not settings.SMTP_HOST:
        logger.warning(
            "[DEV MODE] Chua cau hinh SMTP_HOST nen khong gui email that. "
            "Ma OTP dat lai mat khau cho %s la: %s (het han sau %s phut).",
            to_email, otp, settings.OTP_EXPIRE_MINUTES,
        )
        return

    msg = EmailMessage()
    msg["Subject"] = "Ma OTP dat lai mat khau FAMS"
    msg["From"] = settings.MAIL_FROM
    msg["To"] = to_email
    msg.set_content(
        f"Ma OTP dat lai mat khau cua ban la: {otp}\n"
        f"Ma co hieu luc trong {settings.OTP_EXPIRE_MINUTES} phut va chi dung duoc 1 lan.\n\n"
        "Neu ban khong yeu cau dat lai mat khau, vui long bo qua email nay."
    )

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        server.starttls()
        if settings.SMTP_USER:
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.send_message(msg)
