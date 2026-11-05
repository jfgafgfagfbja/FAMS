import 'package:intl/intl.dart';

const weekdayLabels = ['Thứ 2', 'Thứ 3', 'Thứ 4', 'Thứ 5', 'Thứ 6', 'Thứ 7', 'Chủ nhật'];

String weekdayLabel(int weekday) =>
    weekday >= 0 && weekday < weekdayLabels.length ? weekdayLabels[weekday] : '?';

/// "2026.1" -> "HK1 - 2026-2027".
String formatSemester(String? semester) {
  final match = RegExp(r'^(\d{4})\.(\d)$').firstMatch(semester ?? '');
  if (match == null) return semester ?? '';
  final year = int.parse(match.group(1)!);
  return 'HK${match.group(2)} - $year-${year + 1}';
}

/// Danh sach hoc ky "YYYY.N" tu (nam nay - 1) toi (nam nay + 1), moi nhat truoc.
List<String> semesterOptions() {
  final year = DateTime.now().year;
  return [
    for (var y = year + 1; y >= year - 1; y--)
      for (var term = 3; term >= 1; term--) '$y.$term',
  ];
}

/// "07:30:00" -> "07:30".
String hhmm(String? time) => (time ?? '').length >= 5 ? time!.substring(0, 5) : (time ?? '');

String fmtDate(DateTime? d) => d == null ? '' : DateFormat('dd/MM/yyyy').format(d);
String fmtDateTime(DateTime? d) => d == null ? '' : DateFormat('HH:mm dd/MM/yyyy').format(d);
String fmtTime(DateTime? d) => d == null ? '' : DateFormat('HH:mm:ss').format(d);
String isoDate(DateTime d) => DateFormat('yyyy-MM-dd').format(d);

DateTime dateOnly(DateTime d) => DateTime(d.year, d.month, d.day);

DateTime mondayOf(DateTime d) => dateOnly(d).subtract(Duration(days: d.weekday - 1));

String percent(double ratio, {int digits = 1}) => '${(ratio * 100).toStringAsFixed(digits)}%';

/// So sanh "HH:MM:SS" cua gio hien tai voi chuoi gio tu backend.
String nowHms([DateTime? now]) => DateFormat('HH:mm:ss').format(now ?? DateTime.now());

/// Gio hien tai (HH:MM:SS) co nam trong [from, to] khong - chuoi cung dinh dang nen so sanh tu dien.
bool nowWithin(String from, String to, [DateTime? now]) {
  final hms = nowHms(now);
  return hms.compareTo(from) >= 0 && hms.compareTo(to) <= 0;
}

bool nowAfter(String time, [DateTime? now]) => nowHms(now).compareTo(time) > 0;
bool nowBefore(String time, [DateTime? now]) => nowHms(now).compareTo(time) < 0;

String attendanceStatusLabel(String? status) => switch (status) {
      'present' => 'Có mặt',
      'late' => 'Muộn',
      'absent' => 'Vắng',
      'excused' => 'Có phép',
      'manual' => 'Xác nhận tay',
      null => 'Chưa điểm danh',
      _ => status,
    };

/// 35.4 -> "35 m", 1250 -> "1,3 km".
String distanceLabel(double? meters) {
  if (meters == null) return '';
  if (meters < 1000) return '${meters.round()} m';
  return '${(meters / 1000).toStringAsFixed(1).replaceAll('.', ',')} km';
}

String sourceLabel(String? source) => switch (source) {
      'camera' => 'Camera lớp học',
      'selfie' => 'SV tự chụp',
      'manual' => 'Xác nhận tay',
      null => '',
      _ => source,
    };

String faceStatusLabel(String? status) => switch (status) {
      'approved' => 'Đã duyệt khuôn mặt',
      'pending' => 'Chờ duyệt khuôn mặt',
      'rejected' => 'Khuôn mặt bị từ chối',
      _ => 'Chưa đăng ký khuôn mặt',
    };

String unitTypeLabel(String type) => switch (type) {
      'faculty' => 'Khoa',
      'training' => 'Phòng Đào tạo',
      'student_affairs' => 'Phòng Công tác SV',
      'board' => 'Ban ngành',
      _ => type,
    };

const unitTypes = ['faculty', 'training', 'student_affairs', 'board'];

/// Ten phong de hien thi. Phong lay tu danh muc thuong da co san chu "Phong" trong
/// ten (VD "Phòng 101 — Nhà E2") nen khong them tien to lan nua; lich cu chi luu ma
/// phong dang chu ("401") thi them vao cho de doc.
String roomLabel(String room) {
  final text = room.trim();
  if (text.isEmpty) return 'Chưa có phòng';
  final lower = text.toLowerCase();
  return lower.startsWith('phòng') || lower.startsWith('phong') ? text : 'Phòng $text';
}

const _vietnameseMarks = {
  'a': 'àáạảãâầấậẩẫăằắặẳẵ',
  'e': 'èéẹẻẽêềếệểễ',
  'i': 'ìíịỉĩ',
  'o': 'òóọỏõôồốộổỗơờớợởỡ',
  'u': 'ùúụủũưừứựửữ',
  'y': 'ỳýỵỷỹ',
  'd': 'đ',
};

final _plainLetters = {
  for (final entry in _vietnameseMarks.entries)
    for (final letter in entry.value.split('')) letter: entry.key,
};

/// Chu thuong khong dau, de tim kiem go khong dau van ra ket qua.
String plainText(String text) => text.toLowerCase().split('').map((c) => _plainLetters[c] ?? c).join();
