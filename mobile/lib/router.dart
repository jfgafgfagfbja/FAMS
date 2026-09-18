import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import 'core/auth_controller.dart';
import 'core/roles.dart';
import 'features/admin/class_detail_page.dart';
import 'features/admin/classes_page.dart';
import 'features/admin/face_review_page.dart';
import 'features/admin/lecturers_page.dart';
import 'features/admin/locations_page.dart';
import 'features/admin/parents_page.dart';
import 'features/admin/schedules_page.dart';
import 'features/admin/staff_page.dart';
import 'features/admin/student_detail_page.dart';
import 'features/admin/students_page.dart';
import 'features/admin/units_page.dart';
import 'features/auth/account_page.dart';
import 'features/auth/forgot_password_page.dart';
import 'features/auth/login_page.dart';
import 'features/auth/reset_password_page.dart';
import 'features/auth/splash_page.dart';
import 'features/home/home_page.dart';
import 'features/lecturer/attendance_scan_page.dart';
import 'features/lecturer/reports_page.dart';
import 'features/lecturer/session_records_page.dart';
import 'features/lecturer/sessions_page.dart';
import 'features/office/overview_page.dart';
import 'features/parent/child_attendance_page.dart';
import 'features/parent/children_page.dart';
import 'features/schedule/week_schedule_page.dart';
import 'features/student/enroll_face_page.dart';
import 'features/student/enroll_for_student_page.dart';
import 'features/student/my_attendance_page.dart';
import 'features/student/self_checkin_page.dart';
import 'widgets/app_shell.dart';

const _publicPaths = {'/login', '/forgot-password', '/reset-password'};

/// Vai tro duoc vao tung nhanh duong dan (khop theo tien to). Khop voi nav o app_shell.
const _routeRoles = <String, List<String>>{
  '/my-attendance': [Roles.student],
  '/face': [Roles.student],
  '/self-checkin': [Roles.student],
  '/children': [Roles.parent],
  '/schedule': [Roles.student, Roles.lecturer, Roles.admin, Roles.training, Roles.affairs, Roles.faculty],
  '/sessions': [Roles.lecturer, Roles.admin, Roles.training, Roles.affairs, Roles.faculty],
  '/reports': [Roles.lecturer, Roles.admin, Roles.training, Roles.affairs, Roles.faculty],
  '/classes': [Roles.lecturer, Roles.admin, Roles.training, Roles.affairs, Roles.faculty],
  '/overview': [Roles.admin, Roles.training, Roles.affairs, Roles.faculty, Roles.board],
  '/students': [Roles.admin, Roles.training, Roles.affairs, Roles.faculty],
  '/lecturers': [Roles.admin, Roles.training, Roles.faculty],
  '/class-schedules': [Roles.admin, Roles.training, Roles.affairs, Roles.faculty],
  '/face-review': [Roles.admin, Roles.affairs],
  '/parents': [Roles.admin, Roles.affairs, Roles.training],
  '/enroll-face': [Roles.admin, Roles.affairs, Roles.lecturer],
  '/locations': [Roles.admin, Roles.training],
  '/units': [Roles.admin],
  '/staff': [Roles.admin],
};

bool canAccess(String role, String path) {
  for (final entry in _routeRoles.entries) {
    if (path == entry.key || path.startsWith('${entry.key}/')) {
      return entry.value.contains(role);
    }
  }
  return true;
}

int _id(GoRouterState state, String name) => int.parse(state.pathParameters[name]!);

GoRouter buildRouter(AuthController auth) {
  return GoRouter(
    initialLocation: '/',
    refreshListenable: auth,
    redirect: (context, state) {
      final path = state.matchedLocation;
      switch (auth.status) {
        case AuthStatus.unknown:
          if (path == '/splash') return null;
          return Uri(path: '/splash', queryParameters: {'from': state.uri.toString()}).toString();
        case AuthStatus.unauthenticated:
          return _publicPaths.contains(path) ? null : '/login';
        case AuthStatus.authenticated:
          if (path == '/splash') {
            final from = state.uri.queryParameters['from'];
            return (from == null || from.startsWith('/splash')) ? '/' : from;
          }
          if (_publicPaths.contains(path)) return '/';
          return canAccess(auth.role, path) ? null : '/';
      }
    },
    routes: [
      GoRoute(path: '/splash', builder: (context, state) => const SplashPage()),
      GoRoute(path: '/login', builder: (context, state) => const LoginPage()),
      GoRoute(path: '/forgot-password', builder: (context, state) => const ForgotPasswordPage()),
      GoRoute(
        path: '/reset-password',
        builder: (context, state) => ResetPasswordPage(email: state.uri.queryParameters['email']),
      ),
      ShellRoute(
        builder: (context, state, child) => AppShell(location: state.uri.path, child: child),
        routes: [
          GoRoute(path: '/', builder: (context, state) => const HomePage()),
          GoRoute(path: '/account', builder: (context, state) => const AccountPage()),
          GoRoute(path: '/schedule', builder: (context, state) => const WeekSchedulePage()),
          // Sinh vien
          GoRoute(path: '/my-attendance', builder: (context, state) => const MyAttendancePage()),
          GoRoute(path: '/face', builder: (context, state) => const EnrollFacePage()),
          GoRoute(
            path: '/self-checkin/:sessionId',
            builder: (context, state) => SelfCheckinPage(sessionId: _id(state, 'sessionId'), title: state.extra as String?),
          ),
          // Phu huynh
          GoRoute(path: '/children', builder: (context, state) => const ChildrenPage()),
          GoRoute(
            path: '/children/:studentId',
            builder: (context, state) => ChildAttendancePage(studentId: _id(state, 'studentId')),
          ),
          // Giang vien + phong ban
          GoRoute(path: '/sessions', builder: (context, state) => const SessionsPage()),
          GoRoute(
            path: '/sessions/:sessionId',
            builder: (context, state) => SessionRecordsPage(sessionId: _id(state, 'sessionId')),
          ),
          GoRoute(
            path: '/sessions/:sessionId/scan',
            builder: (context, state) => AttendanceScanPage(sessionId: _id(state, 'sessionId')),
          ),
          GoRoute(
            path: '/reports',
            builder: (context, state) => ReportsPage(initialClassId: int.tryParse(state.uri.queryParameters['class'] ?? '')),
          ),
          GoRoute(path: '/overview', builder: (context, state) => const OverviewPage()),
          GoRoute(path: '/classes', builder: (context, state) => const ClassesPage()),
          GoRoute(
            path: '/classes/:classId',
            builder: (context, state) => ClassDetailPage(classId: _id(state, 'classId')),
          ),
          GoRoute(path: '/students', builder: (context, state) => const StudentsPage()),
          GoRoute(
            path: '/students/:studentId',
            builder: (context, state) => StudentDetailPage(studentId: _id(state, 'studentId')),
          ),
          GoRoute(
            path: '/enroll-face/:studentId',
            builder: (context, state) => EnrollForStudentPage(studentId: _id(state, 'studentId')),
          ),
          GoRoute(path: '/lecturers', builder: (context, state) => const LecturersPage()),
          GoRoute(path: '/class-schedules', builder: (context, state) => const SchedulesPage()),
          GoRoute(path: '/face-review', builder: (context, state) => const FaceReviewPage()),
          GoRoute(path: '/parents', builder: (context, state) => const ParentsPage()),
          GoRoute(path: '/locations', builder: (context, state) => const LocationsPage()),
          GoRoute(path: '/units', builder: (context, state) => const UnitsPage()),
          GoRoute(path: '/staff', builder: (context, state) => const StaffPage()),
        ],
      ),
    ],
    errorBuilder: (context, state) => Scaffold(
      body: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text('Không tìm thấy trang'),
            TextButton(onPressed: () => context.go('/'), child: const Text('Về trang chủ')),
          ],
        ),
      ),
    ),
  );
}
