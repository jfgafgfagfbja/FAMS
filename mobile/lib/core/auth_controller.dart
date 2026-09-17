import 'package:flutter/foundation.dart';

import '../models/models.dart';
import 'api_client.dart';

enum AuthStatus { unknown, unauthenticated, authenticated }

/// Trang thai dang nhap toan app. GoRouter lang nghe de dieu huong.
class AuthController extends ChangeNotifier {
  AuthController(this.api) {
    api.onSessionExpired = _onSessionExpired;
  }

  final ApiClient api;

  AuthStatus status = AuthStatus.unknown;
  Me? me;

  /// Loi khi khoi dong (vd mat mang) - man hinh cho hien nut thu lai.
  String? bootstrapError;

  /// Thong bao hien o man dang nhap (vd phien het han).
  String? notice;

  String get role => me?.role ?? '';

  Future<void> bootstrap() async {
    bootstrapError = null;
    status = AuthStatus.unknown;
    notifyListeners();

    await api.init();
    if (!api.hasSession) {
      status = AuthStatus.unauthenticated;
      notifyListeners();
      return;
    }
    try {
      me = await _fetchMe();
      status = AuthStatus.authenticated;
    } on ApiException catch (e) {
      if (e.statusCode == 401) {
        await api.clearSession();
        status = AuthStatus.unauthenticated;
      } else {
        bootstrapError = e.message;
      }
    }
    notifyListeners();
  }

  Future<void> login(String email, String password) async {
    await api.login(email, password);
    me = await _fetchMe();
    notice = null;
    status = AuthStatus.authenticated;
    notifyListeners();
  }

  Future<void> reloadMe() async {
    me = await _fetchMe();
    notifyListeners();
  }

  Future<void> logout() async {
    await api.logout();
    me = null;
    status = AuthStatus.unauthenticated;
    notifyListeners();
  }

  Future<Me> _fetchMe() async => Me.fromJson(await api.get('/auth/me') as Map<String, dynamic>);

  void _onSessionExpired() {
    if (status != AuthStatus.authenticated) return;
    me = null;
    notice = 'Phiên đăng nhập đã hết hạn, vui lòng đăng nhập lại.';
    status = AuthStatus.unauthenticated;
    notifyListeners();
  }
}
