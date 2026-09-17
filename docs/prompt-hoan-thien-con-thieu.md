# Prompt hoàn thiện các phần còn thiếu (theo checklist bàn giao)

> Dán "BỐI CẢNH CHUNG" (trong `prompt-frontend-theo-mau-DAU.md`) + từng PROMPT.
> Prompt A làm ngay một mình. B–D độc lập, làm theo thứ tự nào cũng được.

---

## PROMPT A — Commit + xác nhận stack Docker chạy đúng

```
[BỐI CẢNH CHUNG]

Nhiệm vụ: đóng gói các thay đổi gần đây và xác nhận stack production còn chạy.

1. Chạy git status + git diff --stat, nhóm thay đổi thành các commit LOGIC
   riêng (backend model/migration, backend endpoint, frontend, docs) — message
   tiếng Việt không dấu, dạng "feat/fix/chore: ...". KHÔNG commit file rác
   (__pycache__, node_modules, .env, evidence/) — bổ sung .gitignore nếu thiếu.
2. docker compose build --no-cache backend frontend, rồi docker compose up -d.
3. Kiểm tra sau khi up:
   - GET / (health) trả ok; alembic upgrade head chạy không lỗi trong log.
   - Login bằng tài khoản seed, gọi thử 1 endpoint mới thêm gần đây.
   - Frontend nginx serve được, proxy /api về backend hoạt động.
4. Báo cáo: danh sách commit đã tạo, kết quả từng bước kiểm tra. Nếu build
   lỗi thì sửa đến khi sạch rồi mới commit phần sửa đó.
KHÔNG push nếu tôi chưa yêu cầu.
```

---

## PROMPT B — Seed face embedding demo + trang SV tự xóa dữ liệu khuôn mặt

```
[BỐI CẢNH CHUNG]

Nhiệm vụ A — seed embedding để clone về demo được ngay:
1. Thêm vào seed.py: tùy chọn --with-faces đọc ảnh mẫu từ backend/seed_faces/
   (mỗi SV 1 thư mục theo student_code, 2-3 ảnh), chạy qua đúng pipeline
   enroll_face rồi set status=approved. Không có thư mục ảnh → bỏ qua, in
   hướng dẫn. KHÔNG commit ảnh khuôn mặt thật vào git — thêm seed_faces/ vào
   .gitignore, viết README trong đó hướng dẫn tự bỏ ảnh vào.
2. Cách nhanh không cần ảnh: thêm --with-fake-faces sinh embedding ngẫu nhiên
   đã normalize (demo UI danh sách/duyệt, không nhận diện thật được) — ghi rõ
   giới hạn trong help text.

Nhiệm vụ B — SV tự quản lý dữ liệu khuôn mặt (quyền riêng tư, GDPR-style):
1. Backend: GET /faces/mine (SV xem embedding của mình: ngày tạo, trạng thái,
   ảnh nguồn nếu có), DELETE /faces/mine (xóa TOÀN BỘ embedding của chính
   mình + thu hồi consent: consent_given=False). Chỉ role student, chỉ dữ
   liệu của mình. Ghi log xóa (bảng audit sẵn có hoặc log file).
2. Frontend: trong trang /enroll thêm mục "Dữ liệu của tôi": danh sách ảnh đã
   đăng ký + trạng thái duyệt, nút "Xóa toàn bộ dữ liệu khuôn mặt" — confirm
   dialog cảnh báo rõ: sẽ không điểm danh tự động được nữa cho đến khi đăng
   ký lại. Xóa xong quay về bước consent.
3. Test: SV A không xóa được dữ liệu SV B; xóa xong recognition không còn
   nhận diện SV đó.
```

---

## PROMPT C — Forgot password

```
[BỐI CẢNH CHUNG]

Nhiệm vụ: luồng quên mật khẩu bằng email OTP.

1. Backend:
   - Bảng password_resets: user_id, otp_hash (băm, KHÔNG lưu OTP thô),
     expires_at (10 phút), used (bool), created_at.
   - POST /auth/forgot-password {email}: luôn trả 200 kèm message chung dù
     email không tồn tại (chống dò email). Rate limit chặt (slowapi sẵn có,
     3 lần/giờ/IP). Sinh OTP 6 số, gửi email.
   - Gửi email: dùng SMTP config từ settings (SMTP_HOST/PORT/USER/PASS,
     MAIL_FROM trong .env.example). Chưa cấu hình SMTP → log OTP ra console
     kèm cảnh báo "DEV MODE" để dev test được.
   - POST /auth/reset-password {email, otp, new_password}: kiểm OTP đúng +
     còn hạn + chưa dùng; đổi mật khẩu (hash_password sẵn có), đánh dấu used,
     thu hồi toàn bộ token đang hoạt động của user (bảng revoked_tokens —
     nếu cần thì thêm cơ chế revoke-all theo user_id + thời điểm).
2. Frontend: /forgot-password (nhập email → thông báo chung), /reset-password
   (nhập OTP + mật khẩu mới 2 lần, validate độ mạnh tối thiểu 8 ký tự).
   Link "Quên mật khẩu?" ở trang /login.
3. Test: OTP sai/hết hạn/dùng lại đều bị từ chối; reset xong token cũ hết hiệu lực.
```

---

## PROMPT D — Test UI Playwright + code-split bundle

```
[BỐI CẢNH CHUNG]

Nhiệm vụ A — E2E test bằng Playwright:
1. Cài @playwright/test trong frontend, config trỏ tới stack docker compose
   (baseURL từ env). Script npm run test:e2e.
2. Viết test cho các luồng chính (dùng tài khoản seed):
   - Login sai → hiện lỗi; login đúng từng role → vào đúng dashboard.
   - GV: mở phiên từ dashboard → vào màn điểm danh → xác nhận tay 1 SV →
     đóng phiên → modal tổng kết đúng số liệu. (Webcam: fake bằng
     launchOptions args --use-fake-device-for-media-stream +
     --use-fake-ui-for-media-stream, không cần camera thật.)
   - SV: xem lịch tuần, trang chuyên cần render đúng dữ liệu vừa điểm danh.
   - Admin: CRUD sinh viên cơ bản, trang duyệt khuôn mặt mở được.
3. Mỗi test độc lập dữ liệu (tạo qua API trong beforeEach hoặc reset DB script).
4. Thêm job e2e vào CI nếu dự án đã có workflow; chưa có thì tạo
   .github/workflows/e2e.yml chạy compose + playwright.

Nhiệm vụ B — giảm bundle (~750KB):
1. Phân tích: vite build với rollup-plugin-visualizer, báo cáo 5 nguồn nặng nhất.
2. Code-split: React.lazy + Suspense theo route (admin/, attendance/, enroll/
   tách chunk riêng — SV không phải tải code admin); manualChunks tách vendor.
3. Kiểm tra sau split: initial chunk < 250KB gzip; các trang vẫn hoạt động
   (chạy lại bộ Playwright ở nhiệm vụ A để xác nhận không vỡ).
4. Báo cáo số liệu trước/sau.
```

---

## PROMPT E — Sửa logic mở phiên điểm danh (check-in sớm + chặn phiên sai)

```
[BỐI CẢNH CHUNG]

Boi canh loi: open_session trong api/sessions.py hien KHONG kiem tra thoi gian,
dan den 3 lo hong: (1) mo duoc phien cho ngay qua khu/tuong lai bat ky,
(2) mo duoc 2 phien trung cho cung schedule + ngay -> SV bi ghi trung record,
(3) session_date khong can khop weekday cua schedule. Ngoai ra SV den som
khong check-in duoc chi vi giang vien chua bam mo phien (khong phai loi code
nhung can ho tro quy trinh).

Nhiệm vụ:
1. Thêm settings.EARLY_OPEN_MINUTES (mặc định 15) vào core/config.py.
2. Sửa open_session — chỉ cho mở phiên khi TẤT CẢ điều kiện sau đúng, sai
   điều kiện nào trả 400 kèm message tiếng Việt rõ ràng cho điều kiện đó:
   a) session_date là hôm nay (theo giờ server).
   b) session_date.weekday() == schedule.weekday (quy ước 0 = thứ 2 sẵn có).
   c) Giờ hiện tại trong khung [start_time - EARLY_OPEN_MINUTES, end_time].
   d) Chưa tồn tại phiên nào (mọi status) của cùng schedule_id + session_date.
3. Chặn ở tầng DB: UniqueConstraint("schedule_id", "session_date") trên
   attendance_sessions + migration Alembic tương ứng. Trước khi viết migration,
   kiểm tra dữ liệu trùng sẵn có và xử lý (giữ phiên mới nhất, log phiên bị bỏ).
4. SV đến sớm trong khung EARLY_OPEN_MINUTES check-in bình thường và tính
   "present" (logic late hiện tại đã đúng — xác nhận lại bằng test, không sửa).
5. Frontend: nút "Mở phiên" trên dashboard GV và lịch tuần chỉ hiện khi trong
   khung giờ hợp lệ; ngoài khung hiện tooltip "Chỉ mở được từ HH:mm". Xử lý
   message 400 từ backend hiển thị toast.
6. Test: mở phiên ngoài khung giờ / sai ngày / sai weekday / trùng phiên đều
   400 đúng message; mở trong khung sớm 15 phút OK; check-in trước giờ học
   ra "present", sau start + LATE_AFTER_MINUTES ra "late".
```

---

## PROMPT F — Admin đổi mật khẩu hộ người dùng

```
[BỐI CẢNH CHUNG]

Boi canh: SV quen mat khau hien khong co duong nao lay lai neu chua cau hinh
SMTP (luong OTP o Prompt C). Can them thao tac admin doi mat khau ho — day la
luong chuan cac truong van dung (SV len phong dao tao xin cap lai).

Nhiệm vụ:
1. Backend — POST /users/{user_id}/reset-password (admin only):
   - Server TỰ SINH mật khẩu tạm 10 ký tự (chữ hoa/thường/số, tránh ký tự dễ
     nhầm 0/O/l/1), KHÔNG cho admin tự nhập (tránh admin đặt pass đoán được).
   - Hash bằng hash_password sẵn có, lưu, và trả mật khẩu tạm dạng plain
     TRONG response DUY NHẤT lần này (không lưu plain ở đâu khác, không log).
   - Thu hồi toàn bộ token đang hoạt động của user đó (cơ chế revoked_tokens
     sẵn có; nếu chưa revoke được theo user thì bổ sung như mô tả Prompt C).
   - Thêm cột must_change_password (bool, default False) vào users + migration:
     đặt True khi admin reset; /auth/login trả kèm cờ này.
2. Bắt đổi mật khẩu lần đăng nhập kế: endpoint POST /auth/change-password
   (mật khẩu cũ + mới; user tự gọi được bất kỳ lúc nào). Khi must_change_password
   = True, frontend sau login điều hướng thẳng tới trang đổi mật khẩu, không
   cho vào trang khác tới khi đổi xong (đổi xong tắt cờ).
3. Frontend:
   - /admin/students (và lecturers): thêm nút "Cấp lại mật khẩu" mỗi dòng →
     confirm → modal hiện mật khẩu tạm MỘT LẦN, nút copy, cảnh báo "sẽ không
     xem lại được, hãy gửi cho sinh viên ngay".
   - Trang /change-password dùng chung (đổi bắt buộc sau reset + đổi tự nguyện
     trong menu user góc phải).
4. Ghi audit: ai reset mật khẩu của ai, lúc nào (bảng audit sẵn có hoặc bảng
   user_audits mới, KHÔNG lưu mật khẩu).
5. Test: role khác admin gọi reset bị 403; sau reset token cũ hết hiệu lực;
   login bằng pass tạm trả must_change_password=true; đổi xong cờ tắt và
   login bình thường.
```

---

## Thứ tự đề xuất

| # | Prompt | Lý do |
|---|---|---|
| 1 | A | Chốt trạng thái sạch trước khi thêm code mới |
| 2 | E | Lỗi logic nghiệp vụ — sửa sớm trước khi dữ liệu thật bị bẩn |
| 3 | F | SV quên mật khẩu là tình huống xảy ra ngay tuần đầu triển khai |
| 4 | B | Demo được ngay khi clone + đóng lỗ hổng quyền riêng tư |
| 5 | C | OTP email tự phục vụ (bổ sung cho F khi có SMTP) |
| 6 | D | Test E2E làm cuối để phủ tất cả; code-split kèm theo |
