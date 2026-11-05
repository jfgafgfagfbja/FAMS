import 'package:fams_app/core/api_client.dart';
import 'package:fams_app/core/auth_controller.dart';
import 'package:fams_app/core/formatters.dart';
import 'package:fams_app/core/roles.dart';
import 'package:fams_app/core/theme.dart';
import 'package:fams_app/core/token_storage.dart';
import 'package:fams_app/models/models.dart';
import 'package:fams_app/router.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';

/// API gia tra du lieu dung khuon backend, du de dung trang chu cua moi vai tro.
class FakeApi extends ApiClient {
  FakeApi(this.role) : super(storage: TokenStorage());

  final String role;

  Json get me => {
        'id': 1,
        'email': 'nguoi.dung@fams.edu.vn',
        'full_name': 'Nguyễn Văn Thử',
        'role': role,
        'classes': [
          {'id': 1, 'class_code': 'INT3306.1', 'subject_name': 'Phát triển ứng dụng web', 'semester': '2026.1'},
          {'id': 2, 'class_code': 'INT3401.2', 'subject_name': 'Trí tuệ nhân tạo', 'semester': '2026.1'},
        ],
        if (role == Roles.student) ...{
          'student_id': 7,
          'student_code': 'SV0001',
          'major': 'Công nghệ thông tin',
          'cohort': 23,
          'consent_given': true,
          'face_status': 'approved',
          'faculty_name': 'Khoa Công nghệ thông tin',
        },
        if (role == Roles.lecturer) ...{
          'lecturer_id': 3,
          'lecturer_code': 'GV0001',
          'department': 'Bộ môn Hệ thống thông tin',
          'faculty_name': 'Khoa Công nghệ thông tin',
        },
        if (Roles.isStaff(role)) ...{'unit_name': 'Khoa Công nghệ thông tin', 'unit_type': 'faculty', 'position': 'Trưởng Khoa'},
      };

  static Json _attendance(int id, String code, String subject, int absent, bool warning) => {
        'class_id': id,
        'class_code': code,
        'subject_name': subject,
        'semester': '2026.1',
        'present': 12 - absent,
        'absent': absent,
        'total_sessions': 12,
        'absent_ratio': absent / 12,
        'warn_ratio': 0.2,
        'warning': warning,
      };

  @override
  Future<dynamic> get(String path, {Map<String, dynamic>? query}) async {
    return switch (path) {
      '/auth/me' => me,
      '/schedules/week' => [
          {
            'date': isoDate(DateTime.now()),
            'weekday': DateTime.now().weekday - 1,
            'schedule_id': 1,
            'class_id': 1,
            'class_code': 'INT3306.1',
            'subject_name': 'Phát triển ứng dụng web',
            'room': 'E2-101',
            'start_time': '07:00:00',
            'end_time': '09:00:00',
            'session_id': 5,
            'session_status': 'open',
          },
        ],
      '/students/me/attendance' => [
          _attendance(1, 'INT3306.1', 'Phát triển ứng dụng web', 1, false),
          _attendance(2, 'INT3401.2', 'Trí tuệ nhân tạo', 3, true),
          _attendance(3, 'INT3507.1', 'Kiểm thử phần mềm', 0, false),
        ],
      '/lecturers/me/today-schedules' => [
          {
            'schedule_id': 1,
            'class_id': 1,
            'class_code': 'INT3306.1',
            'subject_name': 'Phát triển ứng dụng web',
            'start_time': '07:00:00',
            'end_time': '09:00:00',
            'room': 'E2-101',
            'open_from': '06:45:00',
          },
        ],
      '/reports/overview' => {
          'scope': 'school',
          'scope_name': 'Toàn trường',
          'semester': '2026.1',
          'semesters': ['2026.1', '2025.2'],
          'totals': {
            'classes': 18,
            'students': 420,
            'lecturers': 24,
            'closed_sessions': 96,
            'records': 900,
            'present': 700,
            'late': 60,
            'manual': 20,
            'absent': 90,
            'excused': 30,
            'attendance_rate': 0.87,
            'absent_rate': 0.1,
            'warned_students': 12,
          },
          'by_faculty': [
            {'faculty_id': 1, 'faculty_code': 'K-CNTT', 'faculty_name': 'Khoa Công nghệ thông tin', 'attendance_rate': 0.9, 'absent_rate': 0.08},
            {'faculty_id': 2, 'faculty_code': 'K-KT', 'faculty_name': 'Khoa Kiến trúc', 'attendance_rate': 0.84, 'absent_rate': 0.13, 'warned_students': 5},
          ],
        },
      '/parents/me/children' => [
          {
            'id': 7,
            'student_code': 'SV0001',
            'full_name': 'Nguyễn Thị Con',
            'major': 'Công nghệ thông tin',
            'faculty_name': 'Khoa Công nghệ thông tin',
            'face_status': 'approved',
            'classes': [
              {'id': 1, 'class_code': 'INT3306.1', 'subject_name': 'Phát triển ứng dụng web', 'semester': '2026.1'},
            ],
          },
        ],
      '/notifications/unread-count' => {'count': 3},
      _ => <dynamic>[],
    };
  }

  @override
  Future<PageResult<Map<String, dynamic>>> getPage(String path, {Map<String, dynamic>? query}) async => const PageResult([], 0);
}

/// Mo ung dung that (router, khung, trang chu) voi tai khoan [role] o co man hinh [size].
Future<void> openApp(WidgetTester tester, String role, Size size, {ThemeData? theme}) async {
  tester.view.physicalSize = size;
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.reset);
  final api = FakeApi(role);
  final auth = AuthController(api)
    ..me = Me.fromJson(api.me)
    ..status = AuthStatus.authenticated;
  await tester.pumpWidget(MultiProvider(
    providers: [
      Provider<ApiClient>.value(value: api),
      ChangeNotifierProvider<AuthController>.value(value: auth),
      ChangeNotifierProvider<ThemeController>(create: (_) => ThemeController(TokenStorage())),
    ],
    child: MaterialApp.router(routerConfig: buildRouter(auth), theme: theme ?? AppTheme.light()),
  ));
  await tester.pumpAndSettle();
}
