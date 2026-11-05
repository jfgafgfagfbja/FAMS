import 'package:fams_app/core/formatters.dart';
import 'package:fams_app/core/roles.dart';
import 'package:fams_app/features/home/home_page.dart';
import 'package:fams_app/models/models.dart';
import 'package:fams_app/router.dart';
import 'package:fams_app/widgets/app_shell.dart';
import 'package:fams_app/widgets/dashboard.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

import 'support/fake_portal.dart';

const _desktop = Size(1440, 900);
const _laptop = Size(1000, 700);
const _phone = Size(390, 844);

const _roles = [
  Roles.admin, Roles.training, Roles.affairs, Roles.faculty, Roles.facultyLeader,
  Roles.board, Roles.lecturer, Roles.student, Roles.parent,
];

ClassAttendance _attendance({bool warning = false}) =>
    ClassAttendance.fromJson({'class_code': 'A', 'semester': '2026.1', 'warning': warning});

Finder _menuItem(String label) => find.widgetWithText(ListTile, label);

void main() {
  // Tran bo cuc (RenderFlex overflow) hay loi LayoutBuilder trong IntrinsicHeight deu lam
  // testWidgets that bai, nen chi can dung trang la da kiem tra.
  for (final role in _roles) {
    for (final size in [_desktop, _laptop, _phone]) {
      testWidgets('trang chu $role o ${size.width.toInt()}px khong tran bo cuc', (tester) async {
        await openApp(tester, role, size);
        expect(find.byType(ProfileCard), findsOneWidget);
        expect(find.byType(TileColumn), findsOneWidget);
      });
    }
  }

  // Khung, mau va le moi anh huong moi trang chu khong rieng trang chu.
  for (final role in _roles) {
    for (final size in [_desktop, _phone]) {
      testWidgets('moi trang trong menu cua $role o ${size.width.toInt()}px khong tran bo cuc', (tester) async {
        await openApp(tester, role, size);
        for (final item in navItemsFor(role)) {
          GoRouter.of(tester.element(find.byType(AppShell))).go(item.path);
          await tester.pumpAndSettle();
          expect(find.byType(AppShell), findsOneWidget, reason: item.path);
        }
      });
    }
  }

  test('nhom menu: khong trung duong dan, moi nhom co muc, moi muc vao duoc', () {
    for (final role in _roles) {
      final groups = navGroupsFor(role);
      expect(groups.every((g) => g.items.isNotEmpty), isTrue, reason: role);
      final paths = navItemsFor(role).map((i) => i.path).toList();
      expect(paths.toSet().length, paths.length, reason: role);
      expect(paths.first, '/', reason: role);
      expect(shortcutsFor(role).any((i) => i.path == '/' || i.path == '/account'), isFalse);
      for (final path in paths) {
        expect(canAccess(role, path), isTrue, reason: '$role -> $path');
      }
    }
  });

  testWidgets('man hinh rong: menu truot ra theo nhom, chon muc thi di trang va dong menu', (tester) async {
    await openApp(tester, Roles.student, _desktop);
    expect(find.byType(NavigationBar), findsNothing);
    expect(find.text('Tìm chức năng…'), findsOneWidget);
    expect(find.text('Nguyễn Văn Thử'), findsWidgets);

    await tester.tap(find.byTooltip('Mở menu'));
    await tester.pumpAndSettle();
    expect(find.text('HỌC TẬP'), findsOneWidget);
    expect(find.byTooltip('Đóng menu'), findsOneWidget);

    await tester.tap(_menuItem('Chuyên cần'));
    await tester.pumpAndSettle();
    expect(find.byTooltip('Mở menu'), findsOneWidget);
    expect(find.byType(HomePage), findsNothing);
  });

  testWidgets('bam ra ngoai thi menu dong', (tester) async {
    await openApp(tester, Roles.admin, _desktop);
    await tester.tap(find.byTooltip('Mở menu'));
    await tester.pumpAndSettle();
    await tester.tapAt(const Offset(1000, 500));
    await tester.pumpAndSettle();
    expect(find.byTooltip('Mở menu'), findsOneWidget);
  });

  testWidgets('o tim kiem: go khong dau ra chuc nang, chon thi mo trang do', (tester) async {
    await openApp(tester, Roles.student, _desktop);
    await tester.enterText(find.byType(TextField), 'chuyen can');
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(InkWell, 'Chuyên cần').last);
    await tester.pumpAndSettle();
    expect(find.byType(HomePage), findsNothing);
    expect(tester.widget<TextField>(find.byType(TextField)).controller!.text, isEmpty);
  });

  testWidgets('sinh vien tren dien thoai: Hom nay nam tren, khong co hang loi tat', (tester) async {
    await openApp(tester, Roles.student, _phone);
    expect(find.byType(NavigationBar), findsOneWidget);
    expect(find.byType(ShortcutGrid), findsNothing);
    final today = tester.getTopLeft(find.textContaining('Hôm nay')).dy;
    final tiles = tester.getTopLeft(find.byType(TileColumn)).dy;
    expect(today, lessThan(tiles));
    expect(find.text('Tự điểm danh'), findsOneWidget);
  });

  testWidgets('sinh vien tren may tinh: co hang loi tat, nut tu diem danh, vong tien do', (tester) async {
    await openApp(tester, Roles.student, _desktop);
    expect(find.byType(ShortcutGrid), findsOneWidget);
    expect(find.text('Tự điểm danh'), findsOneWidget);
    expect(find.text('32/36'), findsOneWidget); // 36 buoi cua 3 lop, vang 4
    expect(find.text('Lớp cảnh báo vắng'), findsOneWidget);
  });

  testWidgets('vai tro khong co chuc nang (Ban nganh) khong hien hang loi tat rong', (tester) async {
    await openApp(tester, Roles.board, _desktop);
    expect(find.byType(ShortcutGrid), findsNothing);
  });

  test('nhac nho cua sinh vien xep theo muc can xu ly', () {
    Me me(Json extra) => Me.fromJson({'role': 'student', ...extra});

    expect(studentReminders(me({'consent_given': false}), const []).single.$2, '/face');

    final outdated = studentReminders(me({'consent_given': true, 'consent_outdated': true, 'face_status': 'approved'}), const []);
    expect(outdated.single.$1, contains('xác nhận lại'));

    final pending = studentReminders(me({'consent_given': true, 'face_status': 'pending'}), [_attendance(warning: true)]);
    expect(pending.map((r) => r.$2), ['/face', '/my-attendance']);

    expect(studentReminders(me({'consent_given': true, 'face_status': 'approved'}), [_attendance()]), isEmpty);
  });

  test('tim kiem khong dau', () {
    expect(plainText('Điểm danh Lịch HỌC'), 'diem danh lich hoc');
    expect(plainText('Nhật ký hệ thống').contains('nhat ky'), isTrue);
  });
}
