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
