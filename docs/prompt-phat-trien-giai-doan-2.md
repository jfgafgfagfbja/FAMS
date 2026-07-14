# Prompt phát triển FAMS — Giai đoạn 2

> Cách dùng: copy từng PROMPT bên dưới dán vào Claude (Claude Code / Cowork) theo thứ tự.
> Mỗi prompt là một phiên làm việc độc lập. Làm xong, test, commit rồi mới chạy prompt tiếp theo.

---

## BỐI CẢNH CHUNG (dán kèm đầu mỗi prompt)

```
Dự án FAMS (Face Attendance Management System) tại D:\FAMS — hệ thống điểm danh
sinh viên bằng nhận diện khuôn mặt.

Hiện trạng:
- backend/ : FastAPI + SQLAlchemy + PostgreSQL/pgvector. Đã có: auth JWT (kèm revoke
  token bảng revoked_tokens), rate limit (slowapi), phân quyền theo vai trò
  (admin/lecturer/student) và theo lớp (core/authz.py), API students/lecturers/classes/
  faces/sessions/reports, face_service.py dùng InsightFace buffalo_l (SCRFD + ArcFace,
  ONNX Runtime CPU), evidence_cleanup.py xóa ảnh bằng chứng hết hạn, seed.py.
- frontend/ : mới chỉ có index.html, chưa có React.
- docs/ : FAMS-thiet-ke.md, architecture.mermaid, erd.mermaid.
- Models: users, students (có consent_given), lecturers, classes, enrollments,
  schedules, attendance_sessions, attendance_records (UNIQUE session_id+student_id,
  status: present/late/absent/manual, confidence, evidence_image), face_embeddings
  (Vector(512)), revoked_tokens.

Quy ước code:
- Đọc kỹ code hiện có trước khi sửa, giữ nguyên style: docstring + comment tiếng Việt
  không dấu, type hints đầy đủ, Mapped[]/mapped_column cho models.
- Không phá vỡ API hiện có. Không viết lại file nếu chỉ cần sửa một phần.
- Ngưỡng/hằng số mới đưa vào core/config.py (settings), không hardcode.
- Sau mỗi thay đổi: liệt kê file đã sửa/tạo và cách test thủ công.
```

---

## PROMPT 1 — Anti-spoofing (ƯU TIÊN CAO NHẤT)

```
[dán BỐI CẢNH CHUNG ở trên]

Nhiệm vụ: thêm anti-spoofing (chống giả mạo bằng ảnh in/ảnh điện thoại/video phát lại)
vào pipeline nhận diện, dùng MiniFASNet (Silent-Face-Anti-Spoofing) chạy ONNX Runtime.

Yêu cầu cụ thể:
1. Tạo backend/app/services/antispoof_service.py:
   - Load model MiniFASNetV2 dạng ONNX (lazy-load như get_engine() trong face_service.py).
   - Hàm check_liveness(img: np.ndarray, bbox) -> tuple[bool, float] trả về
     (is_real, score). Crop mặt theo bbox có scale margin đúng chuẩn MiniFASNet
     (2.7x cho model 2.7_80x80).
   - Hướng dẫn tôi tải file model .onnx từ đâu, đặt vào thư mục nào
     (tạo backend/models/ và đọc đường dẫn từ settings.ANTISPOOF_MODEL_PATH).
2. Tích hợp vào face_service.recognize_frame(): sau detect, trước khi so khớp —
   mặt nào không qua liveness thì trả về status="spoof" kèm score, KHÔNG ghi
   attendance record. Thêm settings.ANTISPOOF_THRESHOLD (mặc định 0.5) và
   settings.ANTISPOOF_ENABLED (bool, mặc định True — để tắt được khi dev máy yếu).
3. Tích hợp vào enroll_face(): ảnh đăng ký cũng phải qua liveness.
4. Cập nhật schemas.RecognizeResult: thêm field liveness_score: float | None và
   giá trị "spoof" cho status.
5. Cập nhật api/sessions.py recognize endpoint: mặt bị đánh dấu spoof vẫn lưu ảnh
   bằng chứng (để admin xem lại ai gian lận) nhưng không tạo record.
6. Viết test backend/tests/test_antispoof.py với ảnh mock (không cần model thật,
   mock check_liveness) kiểm tra: spoof không tạo record, real tạo record bình thường.

Ràng buộc: nếu model chưa tải về (file không tồn tại) và ANTISPOOF_ENABLED=True thì
log warning rõ ràng lúc khởi động và bỏ qua bước liveness thay vì crash.
```

---

## PROMPT 2 — Frontend React

```
[dán BỐI CẢNH CHUNG ở trên]

Nhiệm vụ: dựng frontend React 18 + Vite trong D:\FAMS\frontend (thay index.html hiện tại).

Stack: React 18, Vite, react-router-dom, axios (interceptor gắn JWT + redirect 401
về /login), react-webcam. CSS thuần hoặc CSS module, KHÔNG dùng Tailwind/UI framework
nặng. Tiếng Việt có dấu cho toàn bộ UI.

Các trang theo vai trò:
1. /login — đăng nhập, lưu token, điều hướng theo role.
2. Giảng viên:
   - /dashboard: danh sách lớp của mình, lịch dạy hôm nay, nút "Mở phiên điểm danh".
   - /attendance/:sessionId — MÀN HÌNH QUAN TRỌNG NHẤT:
     * Webcam gửi frame lên POST /sessions/{id}/recognize mỗi 2 giây (điều chỉnh
       được), canvas overlay vẽ bbox + tên SV + confidence lên video.
     * Cột phải: danh sách SV lớp đó, realtime đổi trạng thái (chưa điểm danh /
       có mặt / muộn / spoof-cảnh báo đỏ).
     * Nút xác nhận tay (chọn SV từ danh sách chưa điểm danh), nút đóng phiên
       (hiện tổng kết present/late/absent).
   - /sessions/:id/records — xem & sửa record sau buổi học.
3. Sinh viên:
   - /enroll — đăng ký khuôn mặt: hướng dẫn chụp 3 góc (thẳng/trái/phải), preview
     từng ảnh, hiện thông báo lỗi chất lượng từ API (quá tối, quá mờ, nhiều mặt...),
     checkbox đồng ý sử dụng dữ liệu khuôn mặt (consent) bắt buộc trước khi gửi.
   - /my-attendance — lịch sử điểm danh của bản thân, % vắng từng lớp.
4. Admin: /admin — CRUD sinh viên, giảng viên, lớp, lịch học (bảng đơn giản + form).

Yêu cầu kỹ thuật:
- Đọc backend/app/schemas.py và các file api/*.py để khớp đúng shape request/response,
  KHÔNG bịa endpoint. Nếu thiếu endpoint nào cho UI (vd GET danh sách SV của lớp,
  GET lịch sử điểm danh của SV đang đăng nhập) thì bổ sung vào backend luôn.
- Tạo frontend/.env với VITE_API_URL, README ngắn cách chạy dev.
- Làm xong chạy npm run build để chắc chắn build sạch.
```

---

## PROMPT 3 — Sửa record + audit log

```
[dán BỐI CẢNH CHUNG ở trên]

Nhiệm vụ: cho phép giảng viên sửa kết quả điểm danh, có lưu vết (audit).

1. Model mới AttendanceAudit (bảng attendance_audits): id, record_id FK,
   changed_by FK users.id, old_status, new_status, reason (String 500),
   changed_at (server_default now).
2. Endpoint PATCH /sessions/{session_id}/records/{record_id}:
   - Body: {status: "present"|"late"|"absent"|"excused", reason: str (bắt buộc)}.
   - Chỉ lecturer của lớp đó hoặc admin (dùng ensure_class_access sẵn có).
   - Ghi AttendanceAudit mỗi lần sửa. Thêm status mới "excused" (vắng có phép) —
     cập nhật comment trong models.py và schemas.
3. Endpoint GET /sessions/{session_id}/records/{record_id}/audits — xem lịch sử sửa.
4. Phiên đã đóng vẫn sửa được (thực tế SV nộp đơn phép sau buổi học) nhưng audit
   bắt buộc phải có reason.
5. Test: sửa record tạo audit đúng old/new status; lecturer lớp khác bị 403.
```

---

## PROMPT 4 — pgvector HNSW + multi-frame confirmation

```
[dán BỐI CẢNH CHUNG ở trên]

Nhiệm vụ A — dùng pgvector đúng cách:
1. face_service.py đang load toàn bộ embedding vào Python rồi tính cosine bằng numpy
   (cả enroll_face check trùng lẫn recognize_frame). Chuyển sang query pgvector:
   - recognize_frame: dùng toán tử <=> (cosine distance) + JOIN enrollments để chỉ
     tìm trong SV thuộc lớp, ORDER BY distance LIMIT 1 cho mỗi mặt.
   - enroll_face check trùng: tương tự, tìm embedding gần nhất của SV KHÁC.
2. Tạo index HNSW: thêm vào init_db() hoặc migration —
   CREATE INDEX ... USING hnsw (embedding vector_cosine_ops).
3. Lưu ý similarity = 1 - distance, giữ nguyên ngưỡng trong settings.

Nhiệm vụ B — multi-frame confirmation (giảm nhận nhầm):
1. Thêm settings.CONFIRM_FRAMES (mặc định 2): một SV chỉ được ghi record khi được
   nhận diện đủ N frame (không cần liên tiếp) trong cùng phiên.
2. Đếm số lần nhận diện theo (session_id, student_id) — lưu in-memory dict có khóa
   session, dọn khi đóng phiên (chấp nhận mất khi restart, ghi rõ comment). Trả
   status="confirming" kèm số frame hiện tại khi chưa đủ.
3. Cập nhật schemas + test: đủ N frame mới có record, dưới N thì không.
```

---

## PROMPT 5 — Cảnh báo chuyên cần + xuất báo cáo

```
[dán BỐI CẢNH CHUNG ở trên]

Nhiệm vụ A — cảnh báo chuyên cần:
1. settings.ABSENCE_WARN_RATIO (0.2) — ngưỡng % buổi vắng để cảnh báo.
2. GET /reports/attendance/warnings?class_id= — danh sách SV có
   (absent / tổng buổi đã học) >= ngưỡng, kèm chi tiết số buổi. "excused" không
   tính là vắng.
3. Khi close_session: trả thêm danh sách SV vừa vượt ngưỡng trong response.

Nhiệm vụ B — xuất báo cáo Excel:
1. GET /reports/attendance/export?class_id=&semester= trả file .xlsx (dùng openpyxl):
   - Sheet 1: ma trận SV x buổi học (P/L/A/E/M), cột tổng kết số buổi vắng, % vắng,
     tô đỏ SV vượt ngưỡng.
   - Sheet 2: thống kê tổng hợp lớp.
2. Chỉ lecturer của lớp hoặc admin. Tên file: diemdanh_{class_code}_{semester}.xlsx.
3. Test endpoint trả đúng content-type và mở được file.
```

---

## PROMPT 6 — Vận hành: Docker, Alembic, test nền tảng

```
[dán BỐI CẢNH CHUNG ở trên]

Nhiệm vụ:
1. Alembic: khởi tạo migration cho toàn bộ schema hiện tại (autogenerate baseline),
   hướng dẫn quy trình tạo migration mới. init_db() chỉ còn dùng cho dev/test.
2. docker-compose.yml ở gốc dự án: services db (postgres:16 + pgvector, volume,
   healthcheck), backend (Dockerfile python 3.11-slim, cài onnxruntime CPU, chờ db
   healthy, chạy alembic upgrade head rồi uvicorn), frontend (build Vite, serve bằng
   nginx, proxy /api về backend). File .env.example đầy đủ biến.
3. Test nền tảng: pytest + httpx, conftest.py dùng SQLite in-memory hoặc testcontainers
   postgres (chọn phương án đơn giản chạy được, giải thích lý do). Viết test cho:
   auth (login sai/đúng, token revoke), authz theo lớp (lecturer lớp khác 403),
   luồng session (open -> manual -> close -> absent tự sinh, UNIQUE chống ghi trùng).
4. README.md gốc dự án: kiến trúc tóm tắt, cách chạy dev và chạy docker compose,
   tài khoản seed.
```

---

## Ghi chú thứ tự

| Thứ tự | Prompt | Lý do |
|---|---|---|
| 1 | Anti-spoofing | Lỗ hổng nghiêm trọng nhất — một tấm ảnh vô hiệu cả hệ thống |
| 2 | Frontend | Chưa có UI thì chưa demo/dùng được |
| 3 | Sửa record + audit | Nghiệp vụ bắt buộc trong thực tế |
| 4 | HNSW + multi-frame | Chất lượng & hiệu năng nhận diện |
| 5 | Cảnh báo + export | Giá trị nghiệp vụ cho phòng đào tạo |
| 6 | Docker + Alembic + test | Chuẩn bị triển khai thật |

Có thể đổi 2 và 3 cho nhau nếu muốn demo sớm. Prompt 6 có thể làm song song bất kỳ lúc nào.
