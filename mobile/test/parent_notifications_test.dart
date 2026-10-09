import 'package:fams_app/core/roles.dart';
import 'package:fams_app/models/models.dart';
import 'package:fams_app/router.dart';
import 'package:fams_app/widgets/notification_bell.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('doc thong bao tu backend, phan biet da doc / chua doc', () {
    final unread = AppNotification.fromJson(const {
      'id': 3,
      'kind': 'attendance_absent',
      'title': 'Trần Thị Sinh vắng — INT3306.1',
      'body': 'Trần Thị Sinh (SV0001) vắng buổi học ...',
      'link': '/children/12',
      'created_at': '2026-10-09T08:15:00+07:00',
      'read_at': null,
    });
    expect(unread.isRead, isFalse);
    expect(unread.link, '/children/12');
    expect(unread.createdAt, isNotNull);

    final read = AppNotification.fromJson(const {
      'id': 4,
      'kind': 'attendance_present',
      'title': 't',
      'body': 'b',
      'created_at': '2026-10-09T08:15:00+07:00',
      'read_at': '2026-10-09T09:00:00+07:00',
    });
    expect(read.isRead, isTrue);
    expect(read.link, isNull);
  });

  test('doc tuy chon nhan thong bao cua phu huynh', () {
    final prefs = ParentPreferences.fromJson(const {
      'notify_email': true,
      'notify_present': false,
      'email_available': false,
    });
    expect(prefs.notifyEmail, isTrue);
    expect(prefs.notifyPresent, isFalse);
    expect(prefs.emailAvailable, isFalse);
  });

  test('chuong cua phu huynh mo hop thu, va chi phu huynh vao duoc hop thu', () {
    expect(alertTargetFor(Roles.parent), '/notifications');
    expect(alertLabelFor(Roles.parent), 'thông báo mới');
    expect(canAccess(Roles.parent, '/notifications'), isTrue);
    expect(canAccess(Roles.student, '/notifications'), isFalse);
    expect(canAccess(Roles.admin, '/notifications'), isFalse);
  });
}
