import 'package:fams_app/models/models.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('Me parses staff unit and student fields', () {
    final staff = Me.fromJson({
      'id': 7,
      'email': 'khoa.cntt@fams.edu.vn',
      'full_name': 'Nguyen Thi Giao Vu',
      'role': 'faculty_office',
      'unit_id': 1,
      'unit_name': 'Khoa CNTT',
      'unit_type': 'faculty',
      'classes': [],
    });
    expect(staff.role, 'faculty_office');
    expect(staff.unitName, 'Khoa CNTT');
    expect(staff.studentId, isNull);

    final student = Me.fromJson({
      'id': 3,
      'email': 'sv01@fams.edu.vn',
      'full_name': 'Tran Thi Sinh',
      'role': 'student',
      'student_id': 1,
      'consent_given': true,
      'face_status': 'pending',
      'classes': [
        {'id': 1, 'class_code': 'A', 'subject_name': 'Mon A', 'semester': '2025.2'},
        {'id': 2, 'class_code': 'B', 'subject_name': 'Mon B', 'semester': '2026.1'},
        {'id': 3, 'class_code': 'C', 'subject_name': 'Mon C', 'semester': '2026.1'},
      ],
    });
    expect(student.semesters, ['2026.1', '2025.2']);
    expect(student.faceStatus, 'pending');
    expect(student.consentOutdated, isFalse);  // may chu cu khong gui truong nay
    expect(Me.fromJson({'role': 'student', 'consent_given': true, 'consent_outdated': true}).consentOutdated, isTrue);
  });

  test('Student keeps how consent was recorded; consent policy and audit log parse', () {
    final s = Student.fromJson({
      'id': 1, 'student_code': 'SV1', 'full_name': 'A', 'consent_given': true,
      'consent_version': '2026-10', 'consent_method': 'paper', 'consent_recorded_by': 'ctsv01@fams.edu.vn',
    });
    expect(s.consentMethod, 'paper');
    expect(s.consentRecordedBy, 'ctsv01@fams.edu.vn');
    expect(s.consentVersion, '2026-10');

    final policy = ConsentPolicy.fromJson({
      'version': '2026-10', 'title': 'T', 'items': ['a', 'b'], 'checkbox': 'Toi dong y',
    });
    expect(policy.items, ['a', 'b']);

    final log = AuditLogEntry.fromJson({
      'id': 9, 'created_at': '2026-10-16T08:00:00+07:00', 'actor_email': 'admin@fams.edu.vn',
      'actor_role': 'admin', 'action': 'class.update', 'target_type': 'class', 'target_id': 3,
      'target_label': 'C1', 'success': true, 'detail': '{"lecturer_id": [1, 2]}',
    });
    expect(log.action, 'class.update');
    expect(log.targetId, 3);
    expect(log.success, isTrue);
    expect(log.createdAt, isNotNull);
  });

  test('SessionDetail keeps local date and parses offset datetimes', () {
    final s = SessionDetail.fromJson({
      'id': 5,
      'schedule_id': 2,
      'session_date': '2026-09-17',
      'status': 'open',
      'opened_at': '2026-09-17T07:05:00+07:00',
      'class_id': 1,
      'class_code': 'INT3306.1',
      'subject_name': 'Phat trien Web',
      'room': 'P101',
      'start_time': '07:00:00',
      'end_time': '09:00:00',
      'checkin_deadline': '2026-09-17T09:30:00+07:00',
    });
    expect(s.sessionDate, DateTime(2026, 9, 17));
    expect(s.isOpen, isTrue);
    expect(s.openedAt!.toUtc(), DateTime.utc(2026, 9, 17, 0, 5));
    expect(s.checkinDeadline!.toUtc(), DateTime.utc(2026, 9, 17, 2, 30));
  });

  test('RecognizeResult reads bbox as doubles', () {
    final r = RecognizeResult.fromJson({
      'student_id': 1,
      'student_code': 'SV0001',
      'full_name': 'A',
      'confidence': 0.87,
      'status': 'confirming',
      'bbox': [10, 20, 110, 140],
      'confirm_count': 1,
      'confirm_needed': 2,
    });
    expect(r.bbox, [10.0, 20.0, 110.0, 140.0]);
    expect(r.confirmNeeded, 2);
  });

  test('Location and GPS check-in result parse', () {
    final location = Location.fromJson({
      'id': 2, 'code': 'CS-NUITHANH', 'name': 'Co so chinh', 'latitude': 16.0322,
      'longitude': 108.2213, 'radius_m': 200.0, 'is_default': true,
    });
    expect(location.radiusM, 200.0);
    expect(location.isDefault, isTrue);

    final blocked = SelfCheckinResult.fromJson({
      'status': 'out_of_range', 'message': 'Ban dang cach Co so chinh khoang 1200 m',
      'distance_m': 1200.0, 'allowed_radius_m': 200.0,
    });
    expect(blocked.isLocationProblem, isTrue);
    expect(blocked.distanceM, 1200.0);

    final ok = SelfCheckinResult.fromJson({
      'status': 'recognized', 'confidence': 0.9, 'record_status': 'present',
      'distance_m': 42.0, 'allowed_radius_m': 200.0, 'message': 'Diem danh thanh cong',
    });
    expect(ok.isLocationProblem, isFalse);
    expect(ok.recordStatus, 'present');

    final slot = WeekSlot.fromJson({
      'date': '2026-09-18', 'weekday': 4, 'schedule_id': 1, 'class_id': 1, 'class_code': 'A',
      'subject_name': 'B', 'room': 'C', 'start_time': '07:00:00', 'end_time': '09:00:00',
      'location_name': 'Co so chinh', 'location_radius_m': 200.0,
    });
    expect(slot.locationName, 'Co so chinh');
    expect(slot.locationRadiusM, 200.0);
  });

  test('Overview parses totals and faculty rows', () {
    final o = Overview.fromJson({
      'scope': 'school',
      'scope_name': 'Toan truong',
      'semester': '2026.1',
      'semesters': ['2026.1', '2025.2'],
      'totals': {
        'classes': 2, 'students': 10, 'lecturers': 2, 'closed_sessions': 4, 'records': 40,
        'present': 30, 'late': 4, 'manual': 1, 'absent': 4, 'excused': 1,
        'attendance_rate': 0.875, 'absent_rate': 0.1, 'warned_students': 1,
      },
      'by_faculty': [
        {
          'faculty_id': null, 'faculty_code': null, 'faculty_name': 'Chua gan Khoa',
          'classes': 1, 'students': 5, 'lecturers': 1, 'closed_sessions': 2, 'records': 10,
          'present': 8, 'late': 1, 'manual': 0, 'absent': 1, 'excused': 0,
          'attendance_rate': 0.9, 'absent_rate': 0.1, 'warned_students': 0,
        },
      ],
    });
    expect(o.totals.attendanceRate, 0.875);
    expect(o.byFaculty.single.facultyId, isNull);
    expect(o.byFaculty.single.students, 5);
  });
}
