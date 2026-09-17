import 'package:fams_app/core/roles.dart';
import 'package:fams_app/router.dart';
import 'package:fams_app/widgets/app_shell.dart';
import 'package:fams_app/widgets/notification_bell.dart';
import 'package:flutter_test/flutter_test.dart';

const allRoles = [
  Roles.admin, Roles.lecturer, Roles.student, Roles.parent,
  Roles.training, Roles.affairs, Roles.faculty, Roles.board,
];

void main() {
  test('every nav item is reachable for its role (menu khop voi phan quyen route)', () {
    for (final role in allRoles) {
      for (final item in navItemsFor(role)) {
        expect(canAccess(role, item.path), isTrue, reason: '$role -> ${item.path}');
      }
    }
  });

  test('board only sees overview and account', () {
    expect(navItemsFor(Roles.board).map((i) => i.path), ['/', '/account']);
    for (final path in ['/students', '/classes/1', '/sessions/3', '/reports', '/face-review']) {
      expect(canAccess(Roles.board, path), isFalse, reason: path);
    }
    expect(canAccess(Roles.board, '/overview'), isTrue);
  });

  test('academic vs student management split between offices', () {
    expect(canAccess(Roles.affairs, '/face-review'), isTrue);
    expect(canAccess(Roles.training, '/face-review'), isFalse);
    expect(canAccess(Roles.training, '/lecturers'), isTrue);
    expect(canAccess(Roles.affairs, '/lecturers'), isFalse);
    expect(canAccess(Roles.faculty, '/parents'), isFalse);
    expect(Perms(Roles.training).manageAcademic, isTrue);
    expect(Perms(Roles.training).manageStudents, isFalse);
    expect(Perms(Roles.affairs).manageStudents, isTrue);
    expect(Perms(Roles.faculty).excuseOnly, isTrue);
    expect(Perms(Roles.faculty).operateAttendance, isFalse);
  });

  test('students and parents are kept out of management routes', () {
    for (final path in ['/students', '/classes', '/sessions', '/units', '/staff', '/enroll-face/1']) {
      expect(canAccess(Roles.student, path), isFalse, reason: path);
      expect(canAccess(Roles.parent, path), isFalse, reason: path);
    }
    expect(canAccess(Roles.student, '/self-checkin/5'), isTrue);
    expect(canAccess(Roles.parent, '/children/2'), isTrue);
    expect(canAccess(Roles.lecturer, '/self-checkin/5'), isFalse);
  });

  test('notification bell leads each role to a page it may open', () {
    for (final role in allRoles) {
      final target = alertTargetFor(role);
      expect(target, isNotNull, reason: role);
      expect(canAccess(role, target!), isTrue, reason: '$role -> $target');
    }
    expect(alertTargetFor('unknown'), isNull);
  });

  test('only admin manages units and staff accounts', () {
    for (final role in allRoles) {
      expect(canAccess(role, '/units'), role == Roles.admin, reason: role);
      expect(canAccess(role, '/staff'), role == Roles.admin, reason: role);
    }
  });
}
