# FAMS app (Flutter) — Web, Android, iOS

Một mã nguồn Flutter duy nhất thay cho giao diện React cũ, chạy trên:

- **Web**: giao diện cho quản trị, phòng ban, giảng viên (và cả SV/phụ huynh). Build và phục vụ bằng nginx trong `docker-compose.yml`.
- **Android / iOS**: app cho sinh viên (tự điểm danh selfie + GPS, đăng ký khuôn mặt), phụ huynh, giảng viên (quét camera cả lớp).

## Cấu trúc

```
lib/
├── main.dart, app.dart, router.dart   # khởi động, theme, điều hướng + chặn route theo vai trò
├── core/        # api_client (Dio, tự refresh token), auth_controller, roles (ma trận quyền), formatters, theme
├── models/      # model ánh xạ 1-1 schema backend (backend/app/schemas.py)
├── widgets/     # app_shell (menu theo vai trò), notification_bell (chuông cảnh báo), paged_list, form_dialog, camera_capture…
└── features/
    ├── auth/      # đăng nhập, quên/đặt lại mật khẩu (OTP), tài khoản
    ├── home/      # trang chủ theo vai trò
    ├── schedule/  # lịch tuần (SV tự điểm danh, GV mở phiên, in thời khóa biểu PDF)
    ├── student/   # chuyên cần, tự điểm danh, đăng ký khuôn mặt, dữ liệu của tôi
    ├── parent/    # con em, chuyên cần của con
    ├── lecturer/  # phiên điểm danh, quét camera cả lớp, kết quả phiên, báo cáo + Excel
    ├── office/    # thống kê tổng hợp (P.ĐT, P.CTSV, Khoa, Ban ngành)
    └── admin/     # SV, GV, lớp HP, lịch, địa điểm điểm danh, duyệt khuôn mặt, phụ huynh, đơn vị, cán bộ
```

## Chạy khi phát triển

Cần Flutter SDK 3.47+ (`flutter doctor`). Backend chạy như hướng dẫn ở README gốc.

```bash
flutter pub get
```

**Web** (backend dev ở cổng 8001, nhớ thêm `http://localhost:5174` vào `CORS_ORIGINS` của backend):
```bash
flutter run -d chrome --web-port 5174 --dart-define=API_BASE_URL=http://localhost:8001
```

**Android emulator** (mặc định gọi `http://10.0.2.2:8000` = máy chạy backend):
```bash
flutter run -d emulator-5554
```

**Điện thoại thật**: bấm biểu tượng máy chủ ở màn đăng nhập, nhập `http://<IP-LAN-máy-chạy-backend>:8000`. Bản debug cho phép HTTP; bản release bắt buộc HTTPS.

**iOS**: cần máy Mac + Xcode (`flutter run -d ios`). Quyền camera/vị trí đã khai báo trong `ios/Runner/Info.plist`.

## Kiểm tra

```bash
flutter analyze
flutter test
flutter build web --release --dart-define=API_BASE_URL=/api
flutter build apk --release
```

## Lưu ý

- Font PDF: `assets/fonts/Roboto-*.ttf` (Apache 2.0, giấy phép kèm theo) — cần font có dấu tiếng Việt, font mặc định của gói `pdf` không có.

- Trình duyệt chỉ cho dùng camera trên **HTTPS hoặc localhost**. Triển khai web thật cần reverse proxy HTTPS.
- Ảnh bằng chứng là URL có chữ ký, hết hạn sau `MEDIA_URL_EXPIRE_MINUTES` — kéo để tải lại trang nếu ảnh không hiện.
- Tự điểm danh cần quyền vị trí: lớp có gắn địa điểm sẽ bị chặn nếu ở ngoài bán kính hoặc GPS sai số lớn.
- Màn quét cả lớp: nếu khung mặt bị lệch trái/phải (tùy thiết bị camera trước), bật/tắt **Lật khung**.
