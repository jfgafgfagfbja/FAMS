import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';

import 'config.dart';
import 'token_storage.dart';

class ApiException implements Exception {
  ApiException(this.message, {this.statusCode});

  final String message;
  final int? statusCode;

  @override
  String toString() => message;
}

/// 1 file gui kem request multipart.
class UploadFile {
  const UploadFile(this.field, this.bytes, this.filename);

  final String field;
  final Uint8List bytes;
  final String filename;
}

/// Ket qua trang danh sach co phan trang (tong so ban ghi lay tu header X-Total-Count).
class PageResult<T> {
  const PageResult(this.items, this.total);

  final List<T> items;
  final int total;
}

/// Client HTTP dung chung: gan access token, tu dong doi refresh token khi gap 401
/// (moi luc chi 1 request doi token - QueuedInterceptorsWrapper xep hang cac loi),
/// chuan hoa thong bao loi thanh [ApiException].
class ApiClient {
  ApiClient({required this.storage}) {
    _dio = Dio(BaseOptions(
      baseUrl: _baseUrl,
      connectTimeout: const Duration(seconds: 15),
      receiveTimeout: const Duration(seconds: 60),
    ));
    _dio.interceptors.add(QueuedInterceptorsWrapper(
      onRequest: (options, handler) {
        final token = _accessToken;
        if (token != null && options.headers['Authorization'] == null) {
          options.headers['Authorization'] = 'Bearer $token';
        }
        handler.next(options);
      },
      onError: _onError,
    ));
  }

  final TokenStorage storage;
  late final Dio _dio;
  String _baseUrl = AppConfig.defaultBaseUrl();
  String? _accessToken;
  String? _refreshToken;

  /// Goi khi refresh token cung het han - AuthController dua nguoi dung ve man dang nhap.
  VoidCallback? onSessionExpired;

  String get baseUrl => _baseUrl;
  bool get hasSession => _accessToken != null;

  Future<void> init() async {
    final savedUrl = await storage.read(TokenStorage.serverUrlKey);
    if (savedUrl != null && savedUrl.isNotEmpty) {
      _setBaseUrl(savedUrl);
    }
    _accessToken = await storage.read(TokenStorage.accessTokenKey);
    _refreshToken = await storage.read(TokenStorage.refreshTokenKey);
  }

  void _setBaseUrl(String url) {
    _baseUrl = AppConfig.normalize(url);
    _dio.options.baseUrl = _baseUrl;
  }

  /// Doi may chu (vd chay app tren dien thoai that trong mang LAN). Rong = mac dinh.
  Future<void> setServerUrl(String? url) async {
    final value = (url ?? '').trim();
    await storage.write(TokenStorage.serverUrlKey, value.isEmpty ? null : value);
    _setBaseUrl(value.isEmpty ? AppConfig.defaultBaseUrl() : value);
  }

  Future<void> _saveTokens(Map<String, dynamic> data) async {
    _accessToken = data['access_token'] as String?;
    _refreshToken = (data['refresh_token'] as String?) ?? _refreshToken;
    await storage.write(TokenStorage.accessTokenKey, _accessToken);
    await storage.write(TokenStorage.refreshTokenKey, _refreshToken);
  }

  Future<void> clearSession() async {
    _accessToken = null;
    _refreshToken = null;
    await storage.write(TokenStorage.accessTokenKey, null);
    await storage.write(TokenStorage.refreshTokenKey, null);
  }

  Future<void> _onError(DioException err, ErrorInterceptorHandler handler) async {
    final options = err.requestOptions;
    final isAuthCall = options.path.startsWith('/auth/login') ||
        options.path.startsWith('/auth/refresh') ||
        options.path.startsWith('/auth/logout');
    if (err.response?.statusCode != 401 || isAuthCall || options.extra['retried'] == true) {
      return handler.next(err);
    }

    final sentHeader = options.headers['Authorization'] as String?;
    final tokenAlreadyRotated = _accessToken != null && sentHeader != 'Bearer $_accessToken';
    if (!tokenAlreadyRotated) {
      final refreshToken = _refreshToken;
      if (refreshToken == null) {
        await _expireSession();
        return handler.next(err);
      }
      try {
        final refreshDio = Dio(BaseOptions(baseUrl: _baseUrl));
        final resp = await refreshDio.post<Map<String, dynamic>>(
          '/auth/refresh',
          data: {'refresh_token': refreshToken},
        );
        await _saveTokens(resp.data!);
      } catch (_) {
        await _expireSession();
        return handler.next(err);
      }
    }

    options.extra['retried'] = true;
    options.headers['Authorization'] = 'Bearer $_accessToken';
    if (options.data is FormData) {
      // FormData chi gui duoc 1 lan - tao ban sao de gui lai.
      options.data = (options.data as FormData).clone();
    }
    try {
      handler.resolve(await _dio.fetch<dynamic>(options));
    } on DioException catch (retryError) {
      handler.next(retryError);
    }
  }

  Future<void> _expireSession() async {
    final hadSession = _accessToken != null;
    await clearSession();
    if (hadSession) onSessionExpired?.call();
  }

  // ---------------- Goi API ----------------

  Future<T> _guard<T>(Future<T> Function() call) async {
    try {
      return await call();
    } on DioException catch (e) {
      throw _toApiException(e);
    }
  }

  Future<dynamic> get(String path, {Map<String, dynamic>? query}) =>
      _guard(() async => (await _dio.get<dynamic>(path, queryParameters: _clean(query))).data);

  Future<PageResult<Map<String, dynamic>>> getPage(String path, {Map<String, dynamic>? query}) =>
      _guard(() async {
        final resp = await _dio.get<List<dynamic>>(path, queryParameters: _clean(query));
        final items = (resp.data ?? const []).cast<Map<String, dynamic>>();
        final total = int.tryParse(resp.headers.value('x-total-count') ?? '') ?? items.length;
        return PageResult(items, total);
      });

  Future<dynamic> post(String path, {Object? data}) =>
      _guard(() async => (await _dio.post<dynamic>(path, data: data)).data);

  Future<dynamic> patch(String path, {Object? data}) =>
      _guard(() async => (await _dio.patch<dynamic>(path, data: data)).data);

  Future<dynamic> delete(String path) =>
      _guard(() async => (await _dio.delete<dynamic>(path)).data);

  Future<dynamic> postMultipart(
    String path, {
    Map<String, Object?> fields = const {},
    required List<UploadFile> files,
  }) =>
      _guard(() async {
        final form = FormData();
        fields.forEach((key, value) {
          if (value != null) form.fields.add(MapEntry(key, value.toString()));
        });
        for (final file in files) {
          form.files.add(MapEntry(
            file.field,
            MultipartFile.fromBytes(file.bytes, filename: file.filename, contentType: DioMediaType('image', 'jpeg')),
          ));
        }
        return (await _dio.post<dynamic>(path, data: form)).data;
      });

  Future<Uint8List> getBytes(String path, {Map<String, dynamic>? query}) => _guard(() async {
        final resp = await _dio.get<List<int>>(
          path,
          queryParameters: _clean(query),
          options: Options(responseType: ResponseType.bytes),
        );
        return Uint8List.fromList(resp.data ?? const []);
      });

  /// Dang nhap (form OAuth2) va luu token.
  Future<void> login(String email, String password) => _guard(() async {
        final resp = await _dio.post<Map<String, dynamic>>(
          '/auth/login',
          data: {'username': email, 'password': password},
          options: Options(contentType: Headers.formUrlEncodedContentType),
        );
        await _saveTokens(resp.data!);
      });

  /// Doi mat khau cua nguoi dang dang nhap. Server thu hoi moi phien cu va tra ve token moi
  /// cho chinh phien nay - phai luu ngay, neu khong lan goi sau se bi dang xuat.
  Future<void> changePassword(String currentPassword, String newPassword) => _guard(() async {
        final resp = await _dio.post<Map<String, dynamic>>(
          '/auth/change-password',
          data: {'current_password': currentPassword, 'new_password': newPassword},
        );
        await _saveTokens(resp.data!);
      });

  Future<void> logout() async {
    try {
      await _dio.post<dynamic>('/auth/logout', data: {'refresh_token': _refreshToken});
    } catch (_) {
      // Token het han/mat mang - van xoa phien cuc bo.
    }
    await clearSession();
  }

  /// URL day du cua anh bang chung (API tra ve duong dan /evidence/...?exp=&sig=).
  String mediaUrl(String? path) {
    if (path == null || path.isEmpty) return '';
    if (path.startsWith('http')) return path;
    return '$_baseUrl$path';
  }

  Map<String, dynamic>? _clean(Map<String, dynamic>? query) {
    if (query == null) return null;
    return Map.fromEntries(query.entries.where((e) => e.value != null && e.value != ''));
  }

  ApiException _toApiException(DioException e) {
    final response = e.response;
    final code = response?.statusCode;
    if (response == null) {
      return ApiException('Không kết nối được máy chủ ($_baseUrl). Kiểm tra mạng hoặc địa chỉ máy chủ.');
    }

    String? detail;
    final data = response.data;
    if (data is Map) {
      final raw = data['detail'] ?? data['error'];
      if (raw is String) {
        detail = raw;
      } else if (raw is List) {
        detail = raw
            .map((item) => item is Map ? (item['msg'] ?? '').toString().replaceFirst('Value error, ', '') : '$item')
            .where((msg) => msg.isNotEmpty)
            .join('; ');
      }
    }

    switch (code) {
      case 401:
        return ApiException(detail ?? 'Phiên đăng nhập đã hết hạn, vui lòng đăng nhập lại.', statusCode: code);
      case 403:
        return ApiException(detail ?? 'Bạn không có quyền thực hiện thao tác này.', statusCode: code);
      case 429:
        return ApiException(detail ?? 'Thao tác quá nhiều lần, vui lòng thử lại sau ít phút.', statusCode: code);
      default:
        return ApiException(detail ?? 'Máy chủ gặp lỗi (mã $code).', statusCode: code);
    }
  }
}
