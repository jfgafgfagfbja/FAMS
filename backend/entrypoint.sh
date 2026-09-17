#!/bin/sh
set -e

alembic upgrade head
# --proxy-headers: lay IP that cua nguoi dung tu X-Forwarded-For do nginx gan vao -
# thieu co nay moi request deu mang IP cua nginx va rate limit dang nhap tinh chung ca
# truong. Chi an toan vi cong 8000 chi mo tren 127.0.0.1 (xem docker-compose.yml).
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips "*"
