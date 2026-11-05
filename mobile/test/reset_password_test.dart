import 'package:fams_app/core/roles.dart';
import 'package:fams_app/widgets/app_shell.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

import 'support/fake_portal.dart';

const _desktop = Size(1440, 900);

FakeApi _api(String role) => FakeApi(role)
  ..pages = {
    '/students': [
      {'id': 7, 'student_code': 'SV0001', 'full_name': 'Nguyễn Thị Học', 'face_status': 'approved'},
    ],
    '/lecturers': [
      {'id': 3, 'lecturer_code': 'GV0001', 'full_name': 'Trần Văn Dạy', 'department': '', 'email': 'gv@fams.edu.vn'},
    ],
  };

Future<void> _openMenu(WidgetTester tester, String role, FakeApi api, String path) async {
  await openApp(tester, role, _desktop, api: api);
  GoRouter.of(tester.element(find.byType(AppShell))).go(path);
  await tester.pumpAndSettle();
  // Thanh tren cung ve sau cung trong khung, nen nut dau tien la menu cua dong trong danh sach.
  await tester.tap(find.byType(PopupMenuButton<String>).first);
  await tester.pumpAndSettle();
}

Future<void> _openDialog(WidgetTester tester, FakeApi api) async {
  await _openMenu(tester, Roles.affairs, api, '/students');
  await tester.tap(find.text('Đặt lại mật khẩu'));
  await tester.pumpAndSettle();
}

Finder _field(String label) => find.widgetWithText(TextFormField, label);

void main() {
  test('quyen dat lai mat khau theo vai tro', () {
    expect(Perms(Roles.admin).resetStudentPassword, isTrue);
    expect(Perms(Roles.admin).resetStaffPassword, isTrue);
    expect(Perms(Roles.affairs).resetStudentPassword, isTrue);
    expect(Perms(Roles.affairs).resetStaffPassword, isFalse);
    for (final role in [Roles.training, Roles.faculty, Roles.facultyLeader, Roles.board, Roles.lecturer, Roles.student, Roles.parent]) {
      expect(Perms(role).resetStudentPassword, isFalse, reason: role);
      expect(Perms(role).resetStaffPassword, isFalse, reason: role);
    }
  });

  testWidgets('phong CTSV thay nut dat lai mat khau o sinh vien', (tester) async {
    await _openMenu(tester, Roles.affairs, _api(Roles.affairs), '/students');
    expect(find.text('Đặt lại mật khẩu'), findsOneWidget);
  });

  testWidgets('admin thay nut o giang vien, phong Dao tao thi khong', (tester) async {
    await _openMenu(tester, Roles.admin, _api(Roles.admin), '/lecturers');
    expect(find.text('Đặt lại mật khẩu'), findsOneWidget);
  });

  testWidgets('phong Dao tao sua duoc giang vien nhung khong dat lai mat khau', (tester) async {
    await _openMenu(tester, Roles.training, _api(Roles.training), '/lecturers');
    expect(find.text('Sửa'), findsOneWidget);
    expect(find.text('Đặt lại mật khẩu'), findsNothing);
  });

  testWidgets('mat khau ngan hoac hai lan nhap khac nhau thi khong gui', (tester) async {
    final api = _api(Roles.affairs);
    await _openDialog(tester, api);

    await tester.enterText(_field('Mật khẩu mới'), 'ngan');
    await tester.enterText(_field('Nhập lại mật khẩu mới'), 'ngan');
    await tester.tap(find.widgetWithText(FilledButton, 'Đặt lại'));
    await tester.pumpAndSettle();
    expect(find.text('Tối thiểu 8 ký tự'), findsOneWidget);

    await tester.enterText(_field('Mật khẩu mới'), 'MatKhauMoi#1');
    await tester.enterText(_field('Nhập lại mật khẩu mới'), 'MatKhauKhac#2');
    await tester.tap(find.widgetWithText(FilledButton, 'Đặt lại'));
    await tester.pumpAndSettle();
    expect(find.text('Hai lần nhập không khớp'), findsOneWidget);
    expect(api.posts, isEmpty);
  });

  testWidgets('nhap dung thi goi dung endpoint, chi gui mat khau moi', (tester) async {
    final api = _api(Roles.affairs);
    await _openDialog(tester, api);

    await tester.enterText(_field('Mật khẩu mới'), 'MatKhauMoi#1');
    await tester.enterText(_field('Nhập lại mật khẩu mới'), 'MatKhauMoi#1');
    await tester.tap(find.widgetWithText(FilledButton, 'Đặt lại'));
    await tester.pumpAndSettle();

    expect(api.posts.single.$1, '/students/7/reset-password');
    expect(api.posts.single.$2, {'new_password': 'MatKhauMoi#1'});
    expect(find.text('Đã đặt lại mật khẩu cho Nguyễn Thị Học'), findsOneWidget);
  });
}
