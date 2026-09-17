# FAMS — Face Attendance Management System

Hệ thống quản lý sinh viên tích hợp điểm danh bằng nhận diện khuôn mặt — Trường Đại học Kiến trúc Đà Nẵng.

## Kiến trúc tóm tắt

- **Backend**: FastAPI + SQLAlchemy 2.0 + PostgreSQL 16 (extension `pgvector`).
  - Auth: JWT access token (thu hồi qua `revoked_tokens`/`jti`, thu hồi hàng loạt khi đổi mật khẩu qua `users.token_version`) + **refresh token xoay vòng** cho app mobile (`POST /auth/refresh`, dùng lại token cũ ⇒ thu hồi toàn bộ).
  - Rate limit đăng nhập theo IP thật (uvicorn `--proxy-headers` sau nginx) **và** theo tài khoản (nhiều SV dùng chung IP wifi trường/4G).
  - Phân quyền theo vai trò + phạm vi dữ liệu (`core/authz.py`), xem bảng **Phân quyền** bên dưới.
  - Nhận diện khuôn mặt: InsightFace `buffalo_l` (SCRFD + ArcFace 512 chiều) qua ONNX Runtime CPU; embedding ở cột `Vector(512)` (pgvector), so khớp cosine có index HNSW. Ảnh mặt khi đăng ký chỉ lưu tạm để cán bộ đối chiếu, xóa ngay khi duyệt/từ chối; SV tự xem/xóa dữ liệu khuôn mặt của mình.
  - Chống giả mạo: MiniFASNetV2 ONNX, tự tắt nếu thiếu model (`ANTISPOOF_*`).
  - Xác nhận đa khung hình: SV phải được nhận diện đủ `CONFIRM_FRAMES` lần trong phiên mới ghi điểm danh.
  - Phiên điểm danh: chỉ mở trong khung `[giờ bắt đầu − EARLY_OPEN_MINUTES, giờ kết thúc]`; sau `giờ kết thúc + SESSION_GRACE_MINUTES` không nhận điểm danh và **tự động đóng** (sinh bản ghi vắng).
  - Ảnh bằng chứng trả về dạng **URL có chữ ký HMAC** hết hạn (`MEDIA_URL_EXPIRE_MINUTES`), không còn thư mục `/evidence` công khai.
  - Thời gian trả về kèm múi giờ (`+07:00`). Nhật ký sửa điểm danh bắt buộc lý do (`attendance_audits`). Cảnh báo vắng (`ABSENCE_WARN_RATIO`), xuất Excel, thống kê tổng hợp theo Khoa (`GET /reports/overview`).
- **App (Flutter — `mobile/`)**: một mã nguồn cho **Web, Android, iOS** (Dio + tự refresh token, go_router chặn route theo vai trò, camera, geolocator, fl_chart). Chi tiết: [mobile/README.md](mobile/README.md).
- **Web React cũ (`frontend/`)**: giữ tạm để đối chiếu, không còn được build trong Docker Compose.
- **Triển khai**: `docker-compose.yml` dựng `db` (Postgres 16 + pgvector), `backend` (`alembic upgrade head` rồi `uvicorn`), `frontend` (build Flutter web, nginx proxy `/api/` sang backend).

```
FAMS/
├── docs/                  # Tài liệu thiết kế
├── docker-compose.yml     # db + backend + frontend (Flutter web)
├── backend/               # FastAPI + InsightFace + PostgreSQL/pgvector
│   ├── alembic/           # Migrations (baseline 0b5e1a7c2d90 → head)
│   ├── seed.py            # Dữ liệu mẫu + đơn vị + tài khoản cán bộ
│   ├── tests/             # pytest (Postgres thật)
│   └── app/
│       ├── api/           # auth, students, lecturers, classes, schedules, sessions, faces,
│       │                  # reports, parents, units, staff, media
│       ├── core/          # config, security (JWT/refresh), authz (ma trận quyền), media (URL ký), timeutil
│       ├── services/      # face_service, session_service (đóng/tự đóng phiên), attendance_stats…
│       └── schemas.py
├── mobile/                # App Flutter (Web/Android/iOS)
└── frontend/              # Web React cũ (sẽ gỡ)
```

## Phân quyền

| Chức năng | Admin | P. Đào tạo | P. CTSV | Khoa | Ban ngành |
|---|---|---|---|---|---|
| Tài khoản cán bộ, đơn vị | Sửa | – | – | – | – |
| Lớp học phần, lịch học, ghi danh | Sửa | Sửa | Xem | Xem* | – |
| Hồ sơ & phân công giảng viên | Sửa | Sửa | – | Xem* | – |
| Hồ sơ sinh viên, phụ huynh | Sửa | Xem | Sửa | Xem* (SV) | – |
| Duyệt khuôn mặt | Sửa | – | Sửa | – | – |
| Điểm danh chi tiết + ảnh bằng chứng | Sửa | Xem | Xem | Xem* | – |
| Duyệt "Có phép" / hủy duyệt | Sửa | – | Sửa | Sửa* | – |
| Cảnh báo vắng, xuất Excel | Xem | Xem | Xem | Xem* | – |
| Thống kê tổng hợp (chỉ số liệu) | Xem | Xem | Xem | Xem* | Xem |

\* chỉ trong phạm vi Khoa của mình (SV/GV/lớp được gán `faculty_id`). **Giảng viên**: mở phiên, quét camera, xác nhận tay, sửa điểm danh lớp mình dạy. **Sinh viên**: lịch, tự điểm danh, chuyên cần, dữ liệu khuôn mặt của mình. **Phụ huynh**: chuyên cần của con được liên kết.

Vai trò cán bộ suy ra từ loại đơn vị khi admin tạo tài khoản (`/staff`): Khoa → `faculty_office`, Phòng Đào tạo → `training_office`, Phòng CTSV → `student_affairs`, Ban ngành → `board`.

## Chạy dự án (dev, không dùng Docker)

### Backend
```bash
cd backend
python -m venv venv && venv\Scripts\activate   # Windows
pip install -r requirements.txt
copy .env.example .env                          # sửa DATABASE_URL, SECRET_KEY...
```

Cần Postgres có extension `pgvector` (đơn giản nhất: `docker compose up -d db`). Sau đó:
```bash
alembic upgrade head        # tạo schema (chạy được cả trên database trống)
python seed.py               # dữ liệu mẫu; DB đã có dữ liệu thì chỉ bổ sung đơn vị/cán bộ
uvicorn app.main:app --reload --port 8001
```
API docs: http://localhost:8001/docs

### App Flutter
Xem [mobile/README.md](mobile/README.md). Nhanh nhất (web):
```bash
cd mobile
flutter pub get
flutter run -d chrome --web-port 5174 --dart-define=API_BASE_URL=http://localhost:8001
```

## Chạy bằng Docker Compose

```bash
copy .env.example .env      # sửa POSTGRES_PASSWORD, SECRET_KEY... trước khi lên production
docker compose up --build
docker compose exec backend python seed.py
```

- `db` và `backend` chỉ mở cổng trên `127.0.0.1` (không lộ ra mạng LAN); người dùng truy cập qua `frontend`.
- `frontend`: Flutter web phục vụ bằng nginx ở http://localhost:5173, proxy `/api/*` sang backend.
- Trình duyệt chỉ cho dùng camera trên HTTPS hoặc localhost — triển khai thật cần reverse proxy HTTPS.

## Migrations (Alembic)

```bash
cd backend
alembic upgrade head
alembic revision --autogenerate -m "mo ta thay doi"     # sau khi sửa app/db/models.py, đọc lại file sinh ra
alembic downgrade -1
```

Migration baseline `0b5e1a7c2d90` tạo bảng gốc (trước đây tạo bằng `create_all`), bỏ qua nếu bảng đã tồn tại — nhờ đó `alembic upgrade head` chạy được trên volume mới.

## Test

```bash
cd backend && pytest          # backend (Postgres thật, DB fams_test tạo/xóa tự động)
cd mobile && flutter test     # app Flutter
```

Backend test dùng Postgres thật (cột `Vector(512)` không mock được bằng SQLite), mỗi test trong transaction riêng rồi rollback; bcrypt giảm còn 4 vòng chỉ trong test. Nhóm test chính: auth/refresh token/rate limit, phân quyền theo vai trò và phạm vi Khoa, vòng đời phiên (mở → quét/xác nhận tay → đóng/tự đóng → sinh vắng), duyệt có phép, URL ảnh có chữ ký, dữ liệu khuôn mặt của SV.

## Tài khoản mẫu (seed.py)

| Email | Mật khẩu | Vai trò |
|---|---|---|
| admin@fams.edu.vn | admin123 | Quản trị |
| gv01@fams.edu.vn | gv123 | Giảng viên |
| sv01@fams.edu.vn / sv02@fams.edu.vn | sv123 | Sinh viên |
| ph01@fams.edu.vn | ph123 | Phụ huynh (của sv01) |
| pdt01@fams.edu.vn | pdt12345 | Phòng Đào tạo |
| ctsv01@fams.edu.vn | ctsv1234 | Phòng Công tác SV |
| khoa.cntt@fams.edu.vn | khoa1234 | Văn phòng Khoa CNTT |
| ban01@fams.edu.vn | ban12345 | Ban ngành (Thanh tra) |

## Ghi chú
- Lần chạy đầu, InsightFace tự tải model `buffalo_l` (~300MB).
- Không có GPU vẫn chạy được (ONNX Runtime CPU), ~100–200ms/frame.
- Dữ liệu cũ chưa có Khoa: admin/P.ĐT/P.CTSV gán Khoa cho SV, GV, lớp để cán bộ Khoa thấy dữ liệu.
- Xem `docs/FAMS-thiet-ke.md` để hiểu luồng nghiệp vụ.
