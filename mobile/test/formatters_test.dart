import 'package:fams_app/core/formatters.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('formatSemester', () {
    expect(formatSemester('2026.1'), 'HK1 - 2026-2027');
    expect(formatSemester('khac'), 'khac');
    expect(formatSemester(null), '');
  });

  test('time window helpers compare HH:MM:SS strings', () {
    final now = DateTime(2026, 9, 17, 8, 5, 0);
    expect(nowWithin('07:45:00', '09:30:00', now), isTrue);
    expect(nowWithin('08:10:00', '09:30:00', now), isFalse);
    expect(nowBefore('08:10:00', now), isTrue);
    expect(nowAfter('08:00:00', now), isTrue);
  });

  test('mondayOf returns monday of the same week', () {
    expect(mondayOf(DateTime(2026, 9, 17, 15)), DateTime(2026, 9, 14));
    expect(mondayOf(DateTime(2026, 9, 20)), DateTime(2026, 9, 14));
    expect(mondayOf(DateTime(2026, 9, 14)), DateTime(2026, 9, 14));
  });

  test('labels', () {
    expect(attendanceStatusLabel('excused'), 'Có phép');
    expect(attendanceStatusLabel(null), 'Chưa điểm danh');
    expect(unitTypeLabel('student_affairs'), 'Phòng Công tác SV');
    expect(percent(0.2, digits: 0), '20%');
    expect(semesterOptions().length, 9);
  });
}
