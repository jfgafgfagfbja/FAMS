# Prompt xây dựng Frontend FAMS — thiết kế theo Cổng thông tin sinh viên DAU

> Cách dùng: dán "BỐI CẢNH CHUNG" + từng PROMPT theo thứ tự vào Claude.
> Làm xong prompt nào → chạy thử, commit, rồi mới sang prompt kế tiếp.

---

## BỐI CẢNH CHUNG (dán kèm đầu mọi prompt)

```
Dự án FAMS (Face Attendance Management System) tại D:\FAMS — điểm danh sinh viên
bằng nhận diện khuôn mặt, dùng cho Trường ĐH Kiến trúc Đà Nẵng (DAU).

BACKEND ĐÃ CÓ (FastAPI + SQLAlchemy + PostgreSQL/pgvector, đọc code trước khi làm):
- Auth JWT + revoke (bảng revoked_tokens), rate limit slowapi, phân quyền
  admin/lecturer/student + kiểm tra quyền theo lớp (core/authz.py).
- API: /auth/login, /students, /lecturers, /classes, /faces/enroll,
  /sessions (open/recognize/manual/close/records), /reports/attendance.
- face_service.py: InsightFace buffalo_l, enrollment có kiểm tra chất lượng ảnh
  (mặt ≥112px, độ sáng, độ nét) + chống trùng; recognition giới hạn theo lớp.
- Models: users, students(consent_given), lecturers, classes, enrollments,
  schedules(weekday, start_time, end_time, room), attendance_sessions,
  attendance_records(status: present/late/absent/manual, confidence,
  evidence_image), face_embeddings Vector(512).

FRONTEND HIỆN TẠI: chỉ có frontend/index.html trống — cần xây từ đầu.

CHUẨN THIẾT KẾ: theo Cổng thông tin sinh viên DAU (https://sinhvien.dau.edu.vn)
để sinh viên/giảng viên thấy quen thuộc. Đặc tả thiết kế ở từng prompt.

QUY ƯỚC:
- React 18 + Vite + react-router-dom + axios + react-webcam. CSS module hoặc CSS
  thuần, KHÔNG dùng UI framework nặng. UI tiếng Việt có dấu.
- axios interceptor: gắn Bearer token, 401 → xóa token + về /login.
- Đọc backend/app/schemas.py và api/*.py để khớp đúng request/response — KHÔNG
  bịa endpoint. Thiếu endpoint cho UI thì viết bổ sung vào backend, giữ style
  code hiện có (comment tiếng Việt không dấu, type hints, require_roles,
  ensure_class_access).
- Kết thúc: liệt kê file tạo/sửa, chạy npm run build xác nhận build sạch.

DESIGN SYSTEM (rút từ web DAU):
- Nền xám nhạt #f0f2f5; nội dung là thẻ trắng bo góc 8px, shadow nhẹ.
- Màu chủ đạo đỏ đô (logo DAU) cho header/điểm nhấn; link xanh dương #1976d2.
- Layout: header trắng (logo + tìm kiếm + tên user góc phải) / sidebar trái menu
  gập được (icon + label, mục con thụt vào) / vùng nội dung.
- Thẻ đếm nhanh: số rất to (~40px), nhãn phía trên, link "Xem chi tiết" dưới,
  nền pastel phân biệt (xanh nhạt / vàng nhạt / đỏ nhạt khi cảnh báo).
- Shortcut: hàng thẻ vuông trắng, icon lớn màu xanh ở trên, nhãn dưới.
- Widget dữ liệu: tiêu đề trái + dropdown chọn học kỳ phải, gắn TỪNG widget.
- Học kỳ format "HK{1|2|3} - {YYYY-YYYY}" (vd HK1 - 2025-2026).
- Empty-state: KHÔNG để "Chưa có dữ liệu" trơ trọi như DAU — luôn kèm icon +
  câu gợi ý hành động (vd "Chưa có buổi học nào. Mở phiên điểm danh để bắt đầu").
```

---

## PROMPT 1 — Khung ứng dụng + Đăng nhập + Dashboard theo vai trò

```
[BỐI CẢNH CHUNG]

Nhiệm vụ: khởi tạo frontend Vite React trong D:\FAMS\frontend và làm 3 phần:

1. KHUNG (Layout.jsx): header + sidebar + content theo DESIGN SYSTEM.
   Sidebar theo vai trò:
   - SV: Trang chủ / Lịch học / Chuyên cần của tôi / Đăng ký khuôn mặt
   - GV: Trang chủ / Lịch dạy / Phiên điểm danh / Báo cáo chuyên cần
   - Admin: Trang chủ / Sinh viên / Giảng viên / Lớp học phần / Lịch học /
     Duyệt khuôn mặt
   Route guard theo role, lưu token + user info sau login.

2. /login: thẻ trắng giữa màn hình, logo FAMS, email + mật khẩu, báo lỗi rõ
   (sai mật khẩu / bị rate limit). Đăng nhập xong điều hướng theo role.

3. DASHBOARD — bắt chước bố cục dashboard DAU:
   a) SV (/dashboard):
      - Thẻ thông tin cá nhân: họ tên, MSSV, lớp, ngành (GET từ backend; nếu
        thiếu endpoint /me trả kèm student info thì bổ sung).
      - 3 ô đếm: "Buổi học hôm nay" (xanh nhạt), "Buổi vắng học kỳ này" (vàng
        nhạt), "Lớp sắp vượt ngưỡng vắng" (đỏ nhạt khi >0).
      - Vòng tròn tiến độ chuyên cần từng lớp kiểu "18/20 buổi có mặt" (SVG
        donut, không cần thư viện chart).
   b) GV (/dashboard):
      - 3 ô đếm: "Buổi dạy hôm nay", "Phiên đang mở", "SV vượt ngưỡng vắng".
      - Danh sách buổi dạy hôm nay: mã lớp, môn, giờ, phòng + nút "Mở phiên
        điểm danh" → tạo session rồi chuyển /attendance/{sessionId}.
   c) Hàng shortcut icon kiểu DAU (SV: Lịch tuần / Chuyên cần / Đăng ký khuôn
      mặt; GV: Lịch dạy / Báo cáo / Phiên đang mở).

   Backend cần bổ sung (nếu chưa có): GET /me (user + student/lecturer profile),
   GET /students/me/attendance-summary, GET /lecturers/me/today-schedules,
   GET /sessions?status=open&mine=true. Viết đúng style hiện có + authz.
```

---

## PROMPT 2 — Màn điểm danh webcam (màn hình lõi của FAMS)

```
[BỐI CẢNH CHUNG]

Nhiệm vụ: trang /attendance/:sessionId cho giảng viên — màn hình quan trọng
nhất, DAU không có mẫu tương đương nên thiết kế mới nhưng giữ design system.

Bố cục 2 cột:
1. TRÁI (~65%): video webcam (react-webcam) + canvas overlay vẽ bbox quanh mỗi
   mặt kèm tên + confidence (xanh = nhận diện, đỏ = spoof/unknown). Gửi frame
   JPEG lên POST /sessions/{id}/recognize mỗi N giây (mặc định 2s, chỉnh được
   trên UI, dừng gửi khi tab ẩn). Toast góc phải khi có SV mới được ghi nhận:
   "✓ Nguyễn Văn A — có mặt (0.87)".
2. PHẢI (~35%): danh sách SV của lớp, cập nhật realtime sau mỗi response:
   - Trạng thái màu: xám "chưa điểm danh" / xanh "có mặt" / vàng "muộn" /
     tím "manual" / đỏ nhấp nháy khi phát hiện spoof.
   - Bộ đếm trên đầu: Có mặt x/N • Muộn y • Chưa z (kiểu ô đếm DAU thu nhỏ).
   - Mỗi SV chưa điểm danh có nút "Xác nhận tay" → POST /sessions/{id}/manual.
3. Thanh trên: mã lớp, môn, phòng, giờ, đồng hồ thời gian phiên đang mở, nút
   "Đóng phiên" → confirm dialog → PATCH close → modal tổng kết
   present/late/absent + link sang trang records.

Backend bổ sung nếu thiếu: GET /sessions/{id} (kèm class info) và GET danh sách
SV của lớp kèm trạng thái điểm danh của phiên (endpoint gộp để đỡ N+1 request).

Lưu ý kỹ thuật: chụp frame bằng canvas.toBlob('image/jpeg', 0.8) từ video;
khóa gửi chồng (đợi response mới gửi frame kế); hiển thị lỗi mạng không chặn UI.
```

---

## PROMPT 3 — Lịch tuần dạng lưới (bắt chước "Lịch theo tuần" của DAU)

```
[BỐI CẢNH CHUNG]

Nhiệm vụ: trang /schedule dùng chung cho SV và GV, sao chép pattern trang
"Lịch học, lịch thi theo tuần" của DAU:

1. Lưới: cột = Thứ 2 → Chủ nhật (kèm ngày dd/MM/yyyy), hàng = ca Sáng / Chiều /
   Tối (Sáng: trước 12h, Chiều: 12-18h, Tối: sau 18h theo start_time).
2. Thanh điều hướng: nút "Trở về" / "Hiện tại" / "Tiếp" (lùi/về tuần nay/tới),
   nút "In lịch" (window.print + CSS @media print gọn).
3. Ô lịch: mã lớp, môn, phòng, giờ. KHÁC DAU — thêm badge trạng thái:
   - SV: buổi đã qua hiện ✓ có mặt / M muộn / ✗ vắng (màu tương ứng);
     buổi tương lai hiện giờ học.
   - GV: buổi hôm nay chưa có phiên → nút nhỏ "Mở phiên"; đang mở → badge
     "Đang điểm danh" xanh nhấp nháy, click vào /attendance/{sessionId};
     đã đóng → "x/N có mặt".
4. Chú thích màu cuối trang kiểu DAU (legend các trạng thái).

Backend bổ sung: GET /schedules/week?start=YYYY-MM-DD trả lịch tuần của user
hiện tại (SV: theo enrollments, GV: theo lớp phụ trách) kèm session + record
tương ứng nếu có. Một endpoint duy nhất, tránh N+1.
```

---

## PROMPT 4 — Trang chuyên cần SV (bắt chước "Kết quả học tập" của DAU)

```
[BỐI CẢNH CHUNG]

Nhiệm vụ: trang /my-attendance cho SV, theo pattern widget "Kết quả học tập":

1. Dropdown chọn học kỳ (format "HK1 - 2025-2026") gắn đầu widget. Lưu ý:
   backend đang lưu semester dạng "2026.1" — viết hàm chuyển đổi hiển thị
   2 chiều, VÀ đề xuất (không tự làm) migration đổi format nếu hợp lý.
2. Bảng: mỗi lớp học phần 1 dòng — mã lớp, môn, số buổi Có mặt / Muộn / Vắng /
   Có phép, % vắng, thanh progress nhỏ. Dòng đỏ nhạt khi % vắng ≥ 80% ngưỡng
   cấm thi, kèm icon cảnh báo + tooltip "Vắng thêm N buổi sẽ bị cấm thi".
3. Click dòng → mở rộng chi tiết từng buổi: ngày, trạng thái, giờ ghi nhận,
   ảnh bằng chứng (nếu record của mình) + nút "Khiếu nại" (mở mailto hoặc modal
   ghi chú gửi GV — nếu làm modal thì cần endpoint mới, làm đơn giản).
4. Biểu đồ cột % chuyên cần theo học kỳ (SVG thuần hoặc CSS bar, không thư viện).

Backend bổ sung: GET /students/me/attendance?semester= trả dữ liệu gộp trên.
SV chỉ xem được dữ liệu của chính mình (kiểm tra trong endpoint).
```

---

## PROMPT 5 — Đăng ký khuôn mặt + Duyệt của Admin

```
[BỐI CẢNH CHUNG]

Nhiệm vụ A — trang /enroll cho SV (DAU không có mẫu, giữ design system):
1. Stepper 4 bước kiểu hàng shortcut DAU: Đồng ý điều khoản → Chụp thẳng →
   Nghiêng trái → Nghiêng phải.
2. Bước 1: nội dung consent (dữ liệu khuôn mặt dùng để điểm danh, chỉ lưu
   embedding không lưu được ảnh gốc, có thời hạn ảnh bằng chứng) + checkbox
   bắt buộc; gọi API cập nhật consent_given (bổ sung endpoint nếu thiếu).
3. Mỗi bước chụp: khung webcam + hình bóng mặt hướng dẫn, chụp xong preview +
   gửi /faces/enroll ngay — hiện lỗi chất lượng từ backend (quá tối, mờ, nhiều
   mặt, trùng SV khác) ngay tại bước đó, cho chụp lại không mất bước trước.
4. Hoàn tất: màn hình tổng kết số ảnh thành công + trạng thái "Chờ duyệt".

Nhiệm vụ B — trang /admin/face-approvals:
1. Backend: thêm cột status (pending/approved/rejected) vào face_embeddings
   (mặc định pending), recognition CHỈ dùng embedding approved. Endpoint:
   GET /faces/pending, PATCH /faces/{id}/approve, PATCH /faces/{id}/reject
   (admin only). Cảnh báo trùng (cosine > ngưỡng với SV khác) trả kèm để admin
   thấy khi duyệt.
2. UI: lưới thẻ — mỗi thẻ 1 SV chờ duyệt: ảnh nguồn (nếu lưu), MSSV, tên,
   cảnh báo trùng màu đỏ nếu có, nút Duyệt / Từ chối (kèm lý do).
3. Cập nhật seed.py: embedding seed đặt approved để demo không bị kẹt.
```

---

## PROMPT 6 — CRUD Admin (bắt chước bảng dữ liệu DAU)

```
[BỐI CẢNH CHUNG]

Nhiệm vụ: các trang /admin/students, /admin/lecturers, /admin/classes,
/admin/schedules — bảng trắng kiểu DAU: thanh tìm kiếm trên phải, phân trang,
nút "Thêm mới" đỏ đô, mỗi dòng có Sửa/Xóa (xóa có confirm).

1. Form thêm/sửa trong modal, validate phía client khớp schemas backend.
2. /admin/classes: trong trang chi tiết lớp có tab "Sinh viên" (thêm/xóa
   enrollment, import danh sách từ CSV — parse phía client, gọi API từng dòng,
   hiện tiến độ và dòng lỗi) và tab "Lịch học" (CRUD schedule của lớp).
3. Backend bổ sung nếu thiếu: phân trang + tìm kiếm cho GET /students,
   /classes (limit/offset + q), DELETE các resource (kiểm tra ràng buộc FK,
   trả lỗi rõ ràng tiếng Việt).
4. Học kỳ nhập bằng dropdown sinh tự động (HK1/2/3 các năm gần đây) hiển thị
   format DAU.
```

---

## Thứ tự & lý do

| # | Prompt | Lý do |
|---|---|---|
| 1 | Khung + Login + Dashboard | Nền tảng mọi trang khác, demo được ngay |
| 2 | Màn điểm danh webcam | Giá trị lõi của FAMS |
| 3 | Lịch tuần | Điểm vào tự nhiên để mở phiên, SV xem trạng thái |
| 4 | Chuyên cần SV | Giá trị cho SV, dùng pattern DAU quen thuộc |
| 5 | Enroll + Duyệt | Khép kín vòng đời khuôn mặt |
| 6 | CRUD Admin | Cần cho vận hành thật, làm cuối |

Ghi chú: các prompt backend giai đoạn 2 (anti-spoofing, audit, HNSW...) ở file
`prompt-phat-trien-giai-doan-2.md` — nên chạy Prompt anti-spoofing TRƯỚC hoặc
song song Prompt 2 ở đây, vì màn điểm danh cần hiển thị trạng thái spoof.
