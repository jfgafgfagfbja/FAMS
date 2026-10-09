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

**Web giống lúc triển khai** (web và API chung một địa chỉ như khi chạy sau nginx — dùng để thử camera, ảnh có chữ ký, hoặc mở từ điện thoại trong cùng mạng):

```bash
flutter build web --release --dart-define=API_BASE_URL=/api
python tool/web_proxy.py
```

Mặc định phục vụ `build/web` ở cổng 5180 và chuyển `/api/*` sang `http://127.0.0.1:8000`. Đổi bằng biến môi trường `FAMS_BACKEND`, `FAMS_WEB_DIR`, `FAMS_WEB_PORT`.

**Điện thoại thật**: bấm biểu tượng máy chủ ở màn đăng nhập, nhập `http://<IP-LAN-máy-chạy-backend>:8000`. Bản debug cho phép HTTP; bản release bắt buộc HTTPS.

**iOS**: cần máy Mac + Xcode (`flutter run -d ios`). Quyền camera/vị trí đã khai báo trong `ios/Runner/Info.plist`.

## Kiểm tra

```bash
flutter analyze
flutter test
flutter build web --release --dart-define=API_BASE_URL=/api
flutter build apk --release
```

## Đóng gói bản phát hành

### Android

Bản release phải được ký bằng khoá thật thì mới cài đè bản cũ và mới đưa lên CH Play được. Khoá đọc từ `android/key.properties` — chưa có tệp này thì Gradle tạm ký bằng khoá debug (chỉ dùng để thử).

1. Tạo khoá một lần, cất giữ cẩn thận:

```bash
keytool -genkey -v -keystore D:\khoa\fams-release.jks -storetype JKS -keyalg RSA -keysize 2048 -validity 10000 -alias fams
```

2. Chép `android/key.properties.example` thành `android/key.properties`, điền đường dẫn và mật khẩu. Cả hai tệp `.jks` và `key.properties` đều đã nằm trong `.gitignore`.

3. Đóng gói:

```bash
flutter build apk --release --dart-define=API_BASE_URL=https://fams.truong.edu.vn
```

- `--split-per-abi` cho ra ba tệp nhỏ hơn (arm64, armeabi, x86_64) thay vì một tệp gộp — dùng khi phát cho sinh viên tải trực tiếp.
- `flutter build appbundle --release` cho ra `.aab` để đưa lên CH Play.
- Không truyền `--dart-define` thì app vẫn chạy, người dùng tự nhập địa chỉ máy chủ ở biểu tượng máy chủ trên màn đăng nhập.
- Nếu chạy lệnh trong **Git Bash trên Windows**, giá trị bắt đầu bằng `/` (ví dụ `API_BASE_URL=/api`) sẽ bị đổi thành đường dẫn Windows. Dùng PowerShell, hoặc đặt `MSYS2_ARG_CONV_EXCL='*'` trước lệnh.
- Bản release **bắt buộc HTTPS**: `usesCleartextTraffic` chỉ bật ở bản debug.

### iOS

Cần máy Mac có Xcode, tài khoản Apple Developer và chứng chỉ phân phối. Mã nguồn đã khai báo sẵn tên hiển thị, icon, màn hình chờ, quyền camera/vị trí và khoá `ITSAppUsesNonExemptEncryption`, nên trên Mac chỉ còn các bước:

```bash
flutter build ipa --release --dart-define=API_BASE_URL=https://fams.truong.edu.vn
```

Sau đó mở `build/ios/archive/Runner.xcarchive` bằng Xcode để ký và nộp, hoặc chọn đội ngũ ký trong Xcode ở mục *Runner → Signing & Capabilities* trước khi build. Mã định danh gói là `vn.edu.fams.famsApp`, iOS tối thiểu 15.0.

### Bộ nhận diện

Dấu nhận diện là khung quét khuôn mặt trên nền `#8E1B2E`, trùng `AppColors.brand`. Toàn bộ icon và màn hình chờ của ba nền tảng do [tool/sinh_icon.py](tool/sinh_icon.py) vẽ ra (chỉ cần `pip install pillow`), chạy lại sau khi sửa dấu nhận diện:

```bash
python tool/sinh_icon.py
```

Các tệp được ghi đè:

- Android: `android/app/src/main/res/mipmap-*/ic_launcher*.png`, `drawable-*/splash_logo.png`, màu nền ở `values/colors.xml`.
- iOS: `ios/Runner/Assets.xcassets/AppIcon.appiconset/`, `LaunchImage.imageset/`, màu nền ở `Base.lproj/LaunchScreen.storyboard`.
- Web: `web/favicon.png`, `web/icons/`.

## Lưu ý

- Font PDF: `assets/fonts/Roboto-*.ttf` (Apache 2.0, giấy phép kèm theo) — cần font có dấu tiếng Việt, font mặc định của gói `pdf` không có.

- Trình duyệt chỉ cho dùng camera trên **HTTPS hoặc localhost**. Triển khai web thật cần reverse proxy HTTPS.
- Ảnh bằng chứng là URL có chữ ký, hết hạn sau `MEDIA_URL_EXPIRE_MINUTES` — kéo để tải lại trang nếu ảnh không hiện.
- Tự điểm danh cần quyền vị trí: lớp có gắn địa điểm sẽ bị chặn nếu ở ngoài bán kính hoặc GPS sai số lớn. Nếu người dùng đã từ chối vĩnh viễn, màn hình hiện nút **Mở cài đặt ứng dụng**; nếu máy tắt định vị thì hiện **Mở cài đặt định vị**.
- **Mã QR điểm danh**: GPS chỉ xác nhận sinh viên ở trong khu vực, không biết đúng phòng hay không. Giảng viên bật công tắc *Yêu cầu quét mã QR* ở màn quét lớp rồi chiếu mã lên máy chiếu; mã tự đổi sau mỗi 30 giây nên ảnh chụp màn hình gửi ra ngoài chỉ dùng được trong giây lát. Sinh viên quét mã, hoặc nhập 6 chữ số hiện kèm nếu ngồi cuối phòng không quét được.
- Thư viện quét mã dùng bản MLKit **đóng gói sẵn** nên chạy được cả khi máy không có Google Play, đổi lại APK nặng thêm khoảng 3–10 MB. Muốn nhẹ hơn thì thêm `dev.steenbakker.mobile_scanner.useUnbundled=true` vào `android/gradle.properties`.
- Camera tự nhả khi app chạy nền và mở lại khi quay lại (`CameraLifecycleMixin`). Không có bước này thì trên Android khung xem trước đứng hình, còn iOS báo camera đang bận.
- Màn quét cả lớp: nếu khung mặt bị lệch trái/phải (tùy thiết bị camera trước), bật/tắt **Lật khung**.
