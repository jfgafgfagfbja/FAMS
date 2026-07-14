# FAMS — Face Attendance Management System

Hệ thống quản lý sinh viên tích hợp điểm danh bằng nhận diện khuôn mặt.

## Kiến trúc tóm tắt

- **Backend**: FastAPI + SQLAlchemy 2.0 + PostgreSQL 16 (extension `pgvector`).
  - Auth: JWT (access token) với thu hồi token (`revoked_tokens`, claim `jti`), rate-limit bằng `slowapi`.
  - Phân quyền: theo role (`admin`/`lecturer`/`student`) và theo lớp (giảng viên chỉ thao tác được lớp mình dạy — `core/authz.py`).
  - Nhận diện khuôn mặt: InsightFace `buffalo_l` (SCRFD detector + ArcFace embedding 512 chiều) chạy qua ONNX Runtime CPU. Embedding lưu ở cột `Vector(512)` (pgvector), so khớp bằng cosine distance (`<=>`), có index HNSW.
  - Chống giả mạo (anti-spoofing): MiniFASNetV2 ONNX, tự tắt (no-op) nếu thiếu file model — cấu hình ở `ANTISPOOF_ENABLED/THRESHOLD/MODEL_PATH`.
  - Xác nhận đa khung hình: một sinh viên phải được nhận diện đủ `CONFIRM_FRAMES` khung liên tiếp mới được ghi điểm danh (đếm trong bộ nhớ, không lưu qua restart).
  - Nhật ký chỉnh sửa điểm danh (audit trail): mọi sửa `status` bản ghi điểm danh đều yêu cầu `reason` và được lưu vào `attendance_audits`.
  - Cảnh báo tỷ lệ vắng (`ABSENCE_WARN_RATIO`) và xuất báo cáo Excel (`openpyxl`) — ma trận điểm danh + tổng hợp theo lớp.
  - Schema quản lý bằng Alembic (xem mục Migrations bên dưới). `init_db()` giờ chỉ tạo extension `vector` và chỉ dùng cho dev/test/seed, KHÔNG dùng để tạo bảng ở production.
- **Frontend**: React 18 + Vite, react-router-dom, axios (tự đính JWT, tự điều hướng `/login` khi 401), react-webcam + canvas overlay để vẽ khung nhận diện realtime, Recharts cho biểu đồ, Phosphor icons.
- **Triển khai**: `docker-compose.yml` ở gốc dự án dựng 3 service `db` (Postgres 16 + pgvector), `backend` (chạy `alembic upgrade head` rồi `uvicorn`), `frontend` (build tĩnh bằng Vite, phục vụ bằng nginx, nginx proxy `/api/` sang backend để tránh CORS).

```
FAMS/
├── docs/                  # Tài liệu thiết kế (kiến trúc, ERD, thiết kế chi tiết)
├── docker-compose.yml     # Dựng db + backend + frontend
├── .env.example           # Bien moi truong cho docker-compose (root)
├── backend/               # FastAPI + InsightFace + PostgreSQL/pgvector
│   ├── Dockerfile
│   ├── entrypoint.sh      # alembic upgrade head -> uvicorn
│   ├── alembic/           # Migrations (baseline + các bản sau)
│   ├── seed.py            # Tạo tài khoản/dữ liệu mẫu
│   ├── tests/              # pytest + httpx (Postgres thật, xem mục Test)
│   └── app/
│       ├── main.py        # Entry point
│       ├── core/          # Config, security (JWT)
│       ├── db/            # Database, models SQLAlchemy
│       ├── api/           # Routes: auth, students, classes, faces, sessions, reports
│       ├── services/      # face_service: enrollment + recognition
│       └── schemas.py     # Pydantic schemas
└── frontend/              # React + Vite
    ├── nginx.conf         # Proxy /api/ -> backend (dùng khi build docker)
    └── src/
        ├── pages/         # Login, Dashboard, AttendanceScreen, EnrollFace, ...
        └── api.js         # Axios client
```

## Chạy dự án (dev, không dùng Docker)

### Backend
```bash
cd backend
python -m venv venv && venv\Scripts\activate   # Windows
pip install -r requirements.txt
copy .env.example .env                          # sửa DATABASE_URL, SECRET_KEY...
```

Cần Postgres có sẵn extension `pgvector` (đơn giản nhất: `docker compose up -d db` — xem bên dưới). Sau đó:
```bash
alembic upgrade head        # tạo schema
python seed.py               # (tuỳ chọn) tạo tài khoản/dữ liệu mẫu
uvicorn app.main:app --reload --port 8001
```
API docs: http://localhost:8001/docs

### Frontend
```bash
cd frontend
npm install
npm run dev
```
Mặc định chạy ở http://localhost:5173, gọi thẳng backend qua `VITE_API_URL` (xem `frontend/.env`).

## Chạy bằng Docker Compose (dựng toàn bộ hệ thống)

```bash
copy .env.example .env      # sửa POSTGRES_PASSWORD, SECRET_KEY... trước khi lên production
docker compose up --build
```

- `db`: Postgres 16 + pgvector, dữ liệu lưu ở volume `pgdata`, có healthcheck (`pg_isready`).
- `backend`: build từ Python 3.11-slim, cài `onnxruntime` (CPU). Chờ `db` khoẻ (`service_healthy`) rồi tự chạy `alembic upgrade head` trước khi khởi động `uvicorn` (xem `backend/entrypoint.sh`). Nghe ở `:8000`, evidence ảnh lưu ở volume `evidence`.
- `frontend`: build Vite với `VITE_API_URL=/api` (cố định), phục vụ bằng nginx ở `:80` (map ra host `:5173`). nginx proxy mọi request `/api/*` sang `http://backend:8000/` (xem `frontend/nginx.conf`) để tránh CORS và không lộ địa chỉ nội bộ của backend.

Truy cập frontend tại http://localhost:5173, API tại http://localhost:8000/docs (hoặc qua proxy http://localhost:5173/api/...).

Sau khi lên lần đầu, tạo dữ liệu mẫu (tài khoản chạy trong container backend):
```bash
docker compose exec backend python seed.py
```

## Migrations (Alembic)

Schema bảng được quản lý hoàn toàn bằng Alembic — không dùng `Base.metadata.create_all()` ở production nữa (chỉ `tests/conftest.py` dùng `create_all` để tạo nhanh DB test cô lập, xem mục Test).

```bash
cd backend
alembic upgrade head                                   # áp dụng migration mới nhất
alembic revision --autogenerate -m "mo ta thay doi"     # sau khi sửa app/db/models.py
# --> luôn đọc lại file migration vừa sinh ra trước khi commit, autogenerate
#     không phát hiện được mọi thay đổi (rename cột, thay đổi kiểu dữ liệu phức tạp...)
alembic upgrade head                                   # áp dụng migration vừa tạo
alembic downgrade -1                                   # rollback 1 bước nếu cần
```

## Test

```bash
cd backend
pytest
```

`tests/conftest.py` chạy trên một database Postgres thật (`fams_test`, cùng instance Postgres của dev, xem `DATABASE_URL` trong `.env`/config test), KHÔNG dùng SQLite in-memory hay testcontainers: cột `Vector(512)` (pgvector) dùng trong `Face.embedding` không có kiểu tương đương trong SQLite nên không thể mock bằng SQLite; testcontainers được cân nhắc nhưng bị loại vì nặng hơn và phụ thuộc Docker Desktop ổn định. Schema test được tạo bằng `Base.metadata.create_all()` (nhanh, cô lập với schema Alembic của dev/prod), mỗi test chạy trong một transaction/savepoint riêng rồi rollback (`join_transaction_mode="create_savepoint"`) nên các test độc lập và không cần dọn dữ liệu thủ công.

Các nhóm test chính: auth (đăng nhập đúng/sai, thu hồi token), phân quyền theo lớp (giảng viên lớp khác nhận 403), vòng đời phiên điểm danh đầy đủ (mở → xác nhận tay → đóng → tự sinh vắng cho SV chưa điểm danh), và ràng buộc `UNIQUE(session_id, student_id)` chống ghi trùng bản ghi điểm danh.

## Tài khoản mẫu (seed.py)

| Email | Mật khẩu | Vai trò |
|---|---|---|
| admin@fams.edu.vn | admin123 | admin |
| gv01@fams.edu.vn | gv123 | lecturer |
| sv01@fams.edu.vn | sv123 | student |
| sv02@fams.edu.vn | sv123 | student |

## Ghi chú
- Lần chạy đầu, InsightFace tự tải model `buffalo_l` (~300MB).
- Không có GPU vẫn chạy được (ONNX Runtime CPU), ~100–200ms/frame.
- Xem `docs/FAMS-thiet-ke.md` để hiểu luồng nghiệp vụ.
</content>
