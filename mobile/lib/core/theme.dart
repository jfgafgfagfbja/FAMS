import 'package:flutter/material.dart';

import 'token_storage.dart';

/// Mau nhan dien Truong DH Kien truc Da Nang (dong bo voi web React: --brand, --accent).
class AppColors {
  static const brand = Color(0xFF8E1B2E);
  static const accent = Color(0xFF1976D2);
  static const success = Color(0xFF16A34A);
  static const warning = Color(0xFFC2740A);
  static const danger = Color(0xFFDC2626);
  static const neutral = Color(0xFF6C7280);

  // Bo cuc theo cong thong tin sinh vien cua truong (sinhvien.dau.edu.vn).
  static const pageBackground = Color(0xFFE7ECF0);
  static const muted = Color(0xFF667580);
  static const divider = Color(0xFFE6ECF0);
  static const link = Color(0xFF1DA1F2);
  static const tileBlue = Color(0xFF4DA1E8);
  static const tileBlueBackground = Color(0xFFE0FBFF);
  static const tileAmber = Color(0xFFFF9205);
  static const tileAmberBackground = Color(0xFFFFF2D4);
}

class AppTheme {
  static ThemeData light() => _build(Brightness.light);
  static ThemeData dark() => _build(Brightness.dark);

  static ThemeData _build(Brightness brightness) {
    final isDark = brightness == Brightness.dark;
    final scheme = ColorScheme.fromSeed(
      seedColor: AppColors.brand,
      brightness: brightness,
      primary: isDark ? const Color(0xFFE2626F) : AppColors.brand,
      secondary: isDark ? const Color(0xFF5B7CFF) : AppColors.accent,
      surface: isDark ? const Color(0xFF151822) : Colors.white,
      onSurfaceVariant: isDark ? null : AppColors.muted,
      outlineVariant: isDark ? null : AppColors.divider,
    );
    return ThemeData(
      useMaterial3: true,
      colorScheme: scheme,
      scaffoldBackgroundColor: isDark ? const Color(0xFF0E1016) : AppColors.pageBackground,
      appBarTheme: AppBarTheme(
        backgroundColor: scheme.surface,
        foregroundColor: scheme.onSurface,
        elevation: 1,
        scrolledUnderElevation: 1,
        shadowColor: Colors.black.withValues(alpha: 0.2),
        surfaceTintColor: Colors.transparent,
        toolbarHeight: 57,
        centerTitle: false,
      ),
      cardTheme: CardThemeData(
        elevation: 0,
        margin: EdgeInsets.zero,
        color: scheme.surface,
        surfaceTintColor: Colors.transparent,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(4)),
      ),
      inputDecorationTheme: const InputDecorationTheme(
        border: OutlineInputBorder(),
        isDense: true,
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(4)),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(4)),
        ),
      ),
    );
  }
}

class ThemeController extends ChangeNotifier {
  ThemeController(this.storage);

  final TokenStorage storage;
  ThemeMode mode = ThemeMode.system;

  Future<void> load() async {
    final saved = await storage.read(TokenStorage.themeModeKey);
    mode = switch (saved) {
      'light' => ThemeMode.light,
      'dark' => ThemeMode.dark,
      _ => ThemeMode.system,
    };
    notifyListeners();
  }

  Future<void> setMode(ThemeMode value) async {
    mode = value;
    notifyListeners();
    await storage.write(TokenStorage.themeModeKey, value.name);
  }
}
