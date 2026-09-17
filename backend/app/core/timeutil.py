"""Tra datetime ve client kem mui gio.

Moi cot DateTime trong DB la naive va mang gio dia phuong (container dat TZ=Asia/Ho_Chi_Minh,
DB dat timezone tuong ung - xem migration a18f6c2b9e40). Neu tra ve chuoi khong co offset,
Dart DateTime.parse/JS new Date se tu hieu theo mui gio cua thiet bi -> lech gio khi
thiet bi khong o Viet Nam. LocalDateTime gan offset APP_UTC_OFFSET_MINUTES khi serialize JSON.
"""
from datetime import datetime, timedelta, timezone
from typing import Annotated

from pydantic import PlainSerializer

from app.core.config import settings


def app_timezone() -> timezone:
    return timezone(timedelta(minutes=settings.APP_UTC_OFFSET_MINUTES))


def to_iso_with_offset(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=app_timezone())
    return value.isoformat()


LocalDateTime = Annotated[
    datetime, PlainSerializer(to_iso_with_offset, return_type=str, when_used="json")
]
