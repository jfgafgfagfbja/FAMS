import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Luu token va tuy chon nguoi dung. Android: Keystore, iOS: Keychain,
/// Web: localStorage duoc ma hoa bang WebCrypto (xem flutter_secure_storage).
class TokenStorage {
  static const accessTokenKey = 'fams.access_token';
  static const refreshTokenKey = 'fams.refresh_token';
  static const serverUrlKey = 'fams.server_url';
  static const themeModeKey = 'fams.theme_mode';

  final FlutterSecureStorage _storage = const FlutterSecureStorage();

  Future<String?> read(String key) async {
    try {
      return await _storage.read(key: key);
    } catch (_) {
      // Du lieu ma hoa hong (vd doi thiet bi/xoa key) - coi nhu chua luu.
      return null;
    }
  }

  Future<void> write(String key, String? value) async {
    try {
      if (value == null) {
        await _storage.delete(key: key);
      } else {
        await _storage.write(key: key, value: value);
      }
    } catch (_) {
      // Bo qua: mat token chi khien nguoi dung phai dang nhap lai.
    }
  }
}
