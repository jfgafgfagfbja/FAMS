# FAMS — Face Attendance Management System
## Tài liệu thiết kế hệ thống

## 1. Bối cảnh & mục tiêu

Điểm danh thủ công (gọi tên, ký giấy, quét thẻ) tốn 5–10 phút/buổi, dễ gian lận và phải nhập tay dữ liệu chuyên cần. FAMS tự động hóa: camera nhận diện khuôn mặt sinh viên → ghi nhận điểm danh → đồng bộ vào hệ thống quản lý sinh viên.

**Vai trò:**

| Vai trò | Quyền chính |
|---|---|
| Admin | Quản lý SV, giảng viên, lớp học phần, lịch học; duyệt đăng ký khuôn mặt |
| Giảng viên | Mở/đóng phiên điểm danh, xem & sửa kết quả, thống kê chuyên cần |
| Sinh viên | Đăng ký khuôn mặt, xem lịch sử điểm danh, nhận cảnh báo vắng |

## 2. Kiến trúc

Xem `architecture.mermaid`. Bốn tầng:

1. **Client (React)** — Dashboard quản lý, màn hình điểm danh dùng webcam (gửi frame qua HTTP), trang đăng ký khuôn mặt.
2. **Backend (FastAPI)** — Auth JWT, CRUD nghiệp vụ, API điểm danh, API khuôn mặt.
3. **Face Service (InsightFace)** — pipeline: SCRFD detect → align → anti-spoofing (MiniFASNet) → ArcFace embedding 512d → cosine matching.
4. **PostgreSQL + pgvector** — dữ liệu nghiệp vụ + vector khuôn mặt (index HNSW cho tìm kiếm nhanh).

## 3. Mô hình dữ liệu

Xem `erd.mermaid`. 9 bảng: users, students, lecturers, classes, enrollments, schedules, attendance_sessions, attendance_records, face_embeddings.

Điểm đáng chú ý: embedding lưu `vector(512)` trong pgvector; mỗi SV có 3–5 embedding (nhiều góc mặt); attendance_records có `confidence` và `evidence_image` làm bằng chứng; ràng buộc UNIQUE (session_id, student_id) chống ghi trùng.

## 4. Luồng nghiệp vụ chính

### 4.1 Đăng ký khuôn mặt (enrollment)
1. SV chụp 3–5 ảnh từ webcam (thẳng, nghiêng trái, nghiêng phải).
2. Kiểm tra chất lượng: độ sáng, kích thước mặt ≥ 112px, độ nét, đúng 1 mặt/khung.
3. Detect + align theo 5 landmark → trích embedding 512d.
4. Kiểm tra trùng: nếu cosine similarity với SV khác > 0.6 → cảnh báo admin.
5. Lưu embedding gắn student_id.

### 4.2 Điểm danh (recognition)
1. Giảng viên mở phiên theo lịch lớp học phần.
2. Mỗi frame: detect các mặt → anti-spoofing → trích embedding.
3. So khớp chỉ với embedding của SV **thuộc lớp đó** (giảm nhầm, tăng tốc). Ngưỡng cosine ≥ 0.45 → nhận diện thành công.
4. Ghi record: student_id, thời gian, trạng thái đúng giờ/muộn, confidence, ảnh bằng chứng.
5. Không nhận diện được → giảng viên xác nhận tay (status = manual).
6. Đóng phiên: SV không có record → absent; cập nhật thống kê, cảnh báo vượt ngưỡng vắng.

## 5. API chính

| Method | Endpoint | Mô tả |
|---|---|---|
| POST | /auth/login | Đăng nhập, trả JWT |
| GET/POST | /students | CRUD sinh viên |
| GET/POST | /classes | CRUD lớp học phần |
| POST | /faces/enroll | Đăng ký khuôn mặt (upload ảnh) |
| POST | /sessions | Mở phiên điểm danh |
| POST | /sessions/{id}/recognize | Gửi frame, nhận kết quả nhận diện |
| PATCH | /sessions/{id}/close | Đóng phiên, chốt vắng |
| GET | /reports/attendance | Thống kê chuyên cần |

## 6. Công nghệ

| Thành phần | Lựa chọn |
|---|---|
| Backend | Python 3.11, FastAPI, SQLAlchemy |
| Face | InsightFace (buffalo_l: SCRFD + ArcFace), ONNX Runtime |
| Anti-spoofing | MiniFASNet (giai đoạn 2) |
| DB | PostgreSQL 16 + pgvector |
| Frontend | React 18 + Vite, react-webcam |
| Triển khai | Docker Compose |

## 7. Bảo mật & riêng tư

Chỉ lưu embedding (không đảo ngược được ra ảnh gốc); ảnh bằng chứng lưu có thời hạn; cần sự đồng ý của SV khi đăng ký khuôn mặt; JWT + phân quyền theo vai trò; HTTPS toàn tuyến.
