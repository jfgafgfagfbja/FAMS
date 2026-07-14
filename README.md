# FAMS — Face Attendance Management System

Hệ thống quản lý sinh viên tích hợp điểm danh bằng nhận diện khuôn mặt.

## Cấu trúc

```
FAMS/
├── docs/                  # Tài liệu thiết kế (kiến trúc, ERD, thiết kế chi tiết)
├── backend/               # FastAPI + InsightFace + PostgreSQL/pgvector
│   └── app/
│       ├── main.py        # Entry point
│       ├── core/          # Config, security (JWT)
│       ├── db/            # Database, models SQLAlchemy
│       ├── api/           # Routes: auth, students, classes, faces, sessions, reports
│       ├── services/      # face_service: enrollment + recognition
│       └── schemas.py     # Pydantic schemas
└── frontend/              # React + Vite
    └── src/
        ├── pages/         # Login, Dashboard, AttendanceScreen, EnrollFace
        └── api.js         # Axios client
```

## Chạy dự án

### Backend
```bash
cd backend
python -m venv venv && venv\Scripts\activate   # Windows
pip install -r requirements.txt
copy .env.example .env                          # sửa DATABASE_URL
uvicorn app.main:app --reload
```
API docs: http://localhost:8000/docs

### Database (Docker)
```bash
docker compose up -d db
```

### Migrations (Alembic)
Schema bảng được quản lý bằng Alembic, không dùng `create_all` nữa.
```bash
cd backend
alembic upgrade head          # ap dung migration moi nhat
alembic revision --autogenerate -m "mo ta thay doi"   # khi sua models.py
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## Ghi chú
- Lần chạy đầu, InsightFace tự tải model `buffalo_l` (~300MB).
- Không có GPU vẫn chạy được (ONNX Runtime CPU), ~100–200ms/frame.
- Xem `docs/FAMS-thiet-ke.md` để hiểu luồng nghiệp vụ.
