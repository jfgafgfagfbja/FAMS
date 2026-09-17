import 'package:flutter/foundation.dart';

/// Cau hinh dia chi API.
///
/// Thu tu uu tien: dia chi nguoi dung tu nhap o man hinh dang nhap (luu trong
/// TokenStorage) > --dart-define=API_BASE_URL=... > mac dinh theo nen tang:
/// - Web (build production, phuc vu qua nginx): cung origin, duong dan /api.
/// - Android emulator: 10.0.2.2 tro ve may chu dang chay backend.
/// - iOS simulator / khac: localhost.
class AppConfig {
  static const _definedUrl = String.fromEnvironment('API_BASE_URL');

  static String defaultBaseUrl() {
    if (_definedUrl.isNotEmpty) return normalize(_definedUrl);
    if (kIsWeb) return normalize('/api');
    if (defaultTargetPlatform == TargetPlatform.android) return 'http://10.0.2.2:8000';
    return 'http://localhost:8000';
  }

  /// Bo dau "/" cuoi; tren web bien duong dan tuong doi (/api) thanh URL day du theo
  /// origin hien tai de Dio va Image.network dung chung 1 cach ghep.
  static String normalize(String url) {
    var value = url.trim();
    if (kIsWeb && value.startsWith('/')) {
      value = Uri.base.resolve(value).toString();
    }
    return value.replaceAll(RegExp(r'/+$'), '');
  }
}
