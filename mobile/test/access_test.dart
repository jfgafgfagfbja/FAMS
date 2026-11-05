import 'package:fams_app/core/roles.dart';
import 'package:fams_app/router.dart';
import 'package:fams_app/widgets/app_shell.dart';
import 'package:fams_app/widgets/notification_bell.dart';
import 'package:flutter_test/flutter_test.dart';

const allRoles = [
  Roles.admin, Roles.lecturer, Roles.student, Roles.parent,
  Roles.training, Roles.affairs, Roles.faculty, Roles.facultyLeader, Roles.board,
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
    expect(Perms(Roles.faculty).operateAttendance, isFalse);
  });

  test('van phong Khoa nhap lieu, lanh dao Khoa giam sat + duyet phep', () {
    final office = Perms(Roles.faculty);
    final leader = Perms(Roles.facultyLeader);
    // Van phong Khoa: sua lop/lich/ghi danh trong Khoa, khong duyet phep, khong xem nhat ky.
    expect(office.editClasses, isTrue);
    expect(office.approveExcuse, isFalse);
    expect(office.viewAuditLog, isFalse);
    // Lanh dao Khoa: khong nhap lieu, duoc duyet phep va xem nhat ky Khoa.
    expect(leader.editClasses, isFalse);
    expect(leader.manageAcademic, isFalse);
    expect(leader.manageStudents, isFalse);
    expect(leader.operateAttendance, isFalse);
    expect(leader.approveExcuse, isTrue);
    expect(leader.viewAuditLog, isTrue);
    for (final p in [leader, office]) {
      expect(p.viewStudents && p.viewLecturers && p.viewClasses && p.viewReports, isTrue);
    }
    // Ho so GV, phong hoc, dia diem van chi P.Dao tao/admin sua.
    expect(office.manageAcademic, isFalse);
    expect(Perms(Roles.training).editClasses, isTrue);
    expect(Perms(Roles.affairs).editClasses, isFalse);
  });

  test('only admin and faculty leaders open the audit log', () {
    for (final role in allRoles) {
      final allowed = role == Roles.admin || role == Roles.facultyLeader;
      expect(canAccess(role, '/audit-logs'), allowed, reason: role);
      expect(navItemsFor(role).any((i) => i.path == '/audit-logs'), allowed, reason: role);
    }
  });

  test('every role has a label and a list of duties', () {
    for (final role in allRoles) {
      expect(Roles.label(role), isNot(role), reason: role);
      expect(Roles.duties(role), isNotEmpty, reason: role);
    }
    expect(Roles.isFaculty(Roles.facultyLeader) && Roles.isFaculty(Roles.faculty), isTrue);
    expect(Roles.isStaff(Roles.facultyLeader), isTrue);
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
