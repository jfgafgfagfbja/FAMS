// Model du lieu - anh xa 1-1 voi schema backend (backend/app/schemas.py).

typedef Json = Map<String, dynamic>;

int _i(dynamic v) => (v as num?)?.toInt() ?? 0;
int? _io(dynamic v) => (v as num?)?.toInt();
double _f(dynamic v) => (v as num?)?.toDouble() ?? 0;
double? _fo(dynamic v) => (v as num?)?.toDouble();
String _s(dynamic v) => v?.toString() ?? '';
String? _so(dynamic v) => v?.toString();
bool _b(dynamic v) => v == true;
DateTime? _dt(dynamic v) => v == null ? null : DateTime.tryParse(v.toString())?.toLocal();

/// "2026-09-17" -> DateTime ngay dia phuong (khong lech mui gio).
DateTime _date(dynamic v) {
  final parts = v.toString().split('-').map(int.parse).toList();
  return DateTime(parts[0], parts[1], parts[2]);
}

List<T> _list<T>(dynamic v, T Function(Json) fromJson) =>
    (v as List? ?? const []).map((e) => fromJson(e as Json)).toList();

class ClassBrief {
  ClassBrief.fromJson(Json j)
      : id = _i(j['id']),
        classCode = _s(j['class_code']),
        subjectName = _s(j['subject_name']),
        semester = _s(j['semester']);

  final int id;
  final String classCode;
  final String subjectName;
  final String semester;
}

class Me {
  Me.fromJson(Json j)
      : id = _i(j['id']),
        email = _s(j['email']),
        fullName = _s(j['full_name']),
        role = _s(j['role']),
        studentId = _io(j['student_id']),
        studentCode = _so(j['student_code']),
        major = _so(j['major']),
        cohort = _io(j['cohort']),
        consentGiven = j['consent_given'] as bool?,
        faceStatus = _so(j['face_status']),
        lecturerId = _io(j['lecturer_id']),
        lecturerCode = _so(j['lecturer_code']),
        department = _so(j['department']),
        facultyId = _io(j['faculty_id']),
        facultyName = _so(j['faculty_name']),
        unitId = _io(j['unit_id']),
        unitCode = _so(j['unit_code']),
        unitName = _so(j['unit_name']),
        unitType = _so(j['unit_type']),
        position = _so(j['position']),
        classes = _list(j['classes'], ClassBrief.fromJson);

  final int id;
  final String email;
  final String fullName;
  final String role;
  final int? studentId;
  final String? studentCode;
  final String? major;
  final int? cohort;
  final bool? consentGiven;
  final String? faceStatus;
  final int? lecturerId;
  final String? lecturerCode;
  final String? department;
  final int? facultyId;
  final String? facultyName;
  final int? unitId;
  final String? unitCode;
  final String? unitName;
  final String? unitType;
  final String? position;
  final List<ClassBrief> classes;

  List<String> get semesters => ({for (final c in classes) c.semester}.toList()..sort((a, b) => b.compareTo(a)));
}

class Student {
  Student.fromJson(Json j)
      : id = _i(j['id']),
        studentCode = _s(j['student_code']),
        fullName = _s(j['full_name']),
        major = _s(j['major']),
        cohort = _i(j['cohort']),
        faceEnrolled = _b(j['face_enrolled']),
        faceStatus = _s(j['face_status']).isEmpty ? 'none' : _s(j['face_status']),
        consentGiven = _b(j['consent_given']),
        facultyId = _io(j['faculty_id']),
        facultyName = _so(j['faculty_name']),
        email = _so(j['email']),
        classes = _list(j['classes'], ClassBrief.fromJson);

  final int id;
  final String studentCode;
  final String fullName;
  final String major;
  final int cohort;
  final bool faceEnrolled;
  final String faceStatus;
  final bool consentGiven;
  final int? facultyId;
  final String? facultyName;
  final String? email;

  /// Chi co khi lay qua /parents/me/children.
  final List<ClassBrief> classes;
}

class Lecturer {
  Lecturer.fromJson(Json j)
      : id = _i(j['id']),
        lecturerCode = _s(j['lecturer_code']),
        fullName = _s(j['full_name']),
        department = _s(j['department']),
        email = _so(j['email']),
        facultyId = _io(j['faculty_id']),
        facultyName = _so(j['faculty_name']);

  final int id;
  final String lecturerCode;
  final String fullName;
  final String department;
  final String? email;
  final int? facultyId;
  final String? facultyName;
}

class ClassInfo {
  ClassInfo.fromJson(Json j)
      : id = _i(j['id']),
        classCode = _s(j['class_code']),
        subjectName = _s(j['subject_name']),
        lecturerId = _i(j['lecturer_id']),
        semester = _s(j['semester']),
        facultyId = _io(j['faculty_id']),
        lecturerName = _so(j['lecturer_name']),
        facultyName = _so(j['faculty_name']),
        studentCount = _io(j['student_count']);

  final int id;
  final String classCode;
  final String subjectName;
  final int lecturerId;
  final String semester;
  final int? facultyId;
  final String? lecturerName;
  final String? facultyName;
  final int? studentCount;
}

class ScheduleItem {
  ScheduleItem.fromJson(Json j)
      : id = _i(j['id']),
        classId = _i(j['class_id']),
        weekday = _i(j['weekday']),
        startTime = _s(j['start_time']),
        endTime = _s(j['end_time']),
        room = _s(j['room']),
        roomId = _io(j['room_id']),
        roomName = _so(j['room_name']),
        classCode = _so(j['class_code']),
        subjectName = _so(j['subject_name']),
        locationId = _io(j['location_id']),
        locationName = _so(j['location_name']);

  final int id;
  final int classId;
  final int weekday;
  final String startTime;
  final String endTime;
  final String room;
  final int? roomId;
  final String? roomName;
  final String? classCode;
  final String? subjectName;
  final int? locationId;
  final String? locationName;
}

class WeekSlot {
  WeekSlot.fromJson(Json j)
      : date = _date(j['date']),
        weekday = _i(j['weekday']),
        scheduleId = _i(j['schedule_id']),
        classId = _i(j['class_id']),
        classCode = _s(j['class_code']),
        subjectName = _s(j['subject_name']),
        room = _s(j['room']),
        startTime = _s(j['start_time']),
        endTime = _s(j['end_time']),
        sessionId = _io(j['session_id']),
        sessionStatus = _so(j['session_status']),
        openFrom = _so(j['open_from']),
        myStatus = _so(j['my_status']),
        presentCount = _io(j['present_count']),
        totalCount = _io(j['total_count']),
        locationName = _so(j['location_name']),
        locationRadiusM = _fo(j['location_radius_m']);

  final DateTime date;
  final int weekday;
  final int scheduleId;
  final int classId;
  final String classCode;
  final String subjectName;
  final String room;
  final String startTime;
  final String endTime;
  final int? sessionId;
  final String? sessionStatus;
  final String? openFrom;
  final String? myStatus;
  final int? presentCount;
  final int? totalCount;

  /// Dia diem doi chieu GPS khi SV tu diem danh (null = khong doi chieu).
  final String? locationName;
  final double? locationRadiusM;
}

class TodaySchedule {
  TodaySchedule.fromJson(Json j)
      : scheduleId = _i(j['schedule_id']),
        classId = _i(j['class_id']),
        classCode = _s(j['class_code']),
        subjectName = _s(j['subject_name']),
        startTime = _s(j['start_time']),
        endTime = _s(j['end_time']),
        room = _s(j['room']),
        openFrom = _s(j['open_from']),
        sessionId = _io(j['session_id']),
        sessionStatus = _so(j['session_status']);

  final int scheduleId;
  final int classId;
  final String classCode;
  final String subjectName;
  final String startTime;
  final String endTime;
  final String room;
  final String openFrom;
  final int? sessionId;
  final String? sessionStatus;
}

class SessionDetail {
  SessionDetail.fromJson(Json j)
      : id = _i(j['id']),
        scheduleId = _i(j['schedule_id']),
        sessionDate = _date(j['session_date']),
        status = _s(j['status']),
        openedAt = _dt(j['opened_at']),
        closedAt = _dt(j['closed_at']),
        classId = _i(j['class_id']),
        classCode = _s(j['class_code']),
        subjectName = _s(j['subject_name']),
        room = _s(j['room']),
        startTime = _s(j['start_time']),
        endTime = _s(j['end_time']),
        lecturerName = _so(j['lecturer_name']),
        checkinDeadline = _dt(j['checkin_deadline']),
        requireQr = _b(j['require_qr']),
        locationName = _so(j['location_name']);

  final int id;
  final int scheduleId;
  final DateTime sessionDate;
  final String status;
  final DateTime? openedAt;
  final DateTime? closedAt;
  final int classId;
  final String classCode;
  final String subjectName;
  final String room;
  final String startTime;
  final String endTime;
  final String? lecturerName;
  final DateTime? checkinDeadline;

  /// Buoi nay bat buoc SV quet ma QR dang chieu trong phong moi tu diem danh duoc.
  final bool requireQr;
  final String? locationName;

  bool get isOpen => status == 'open';
}

class RosterEntry {
  RosterEntry.fromJson(Json j)
      : studentId = _i(j['student_id']),
        studentCode = _s(j['student_code']),
        fullName = _s(j['full_name']),
        status = _so(j['status']),
        confidence = _fo(j['confidence']),
        evidenceImage = _so(j['evidence_image']),
        checkedAt = _dt(j['checked_at']),
        recordId = _io(j['record_id']),
        source = _so(j['source']),
        latitude = _fo(j['latitude']),
        longitude = _fo(j['longitude']),
        locationAccuracy = _fo(j['location_accuracy']),
        distanceM = _fo(j['distance_m']);

  final int studentId;
  final String studentCode;
  final String fullName;
  final String? status;
  final double? confidence;
  final String? evidenceImage;
  final DateTime? checkedAt;
  final int? recordId;
  final String? source;
  final double? latitude;
  final double? longitude;
  final double? locationAccuracy;
  final double? distanceM;
}

class RecognizeResult {
  RecognizeResult.fromJson(Json j)
      : studentId = _io(j['student_id']),
        studentCode = _so(j['student_code']),
        fullName = _so(j['full_name']),
        confidence = _f(j['confidence']),
        status = _s(j['status']),
        evidenceImage = _so(j['evidence_image']),
        livenessScore = _fo(j['liveness_score']),
        bbox = (j['bbox'] as List?)?.map((e) => (e as num).toDouble()).toList(),
        confirmCount = _io(j['confirm_count']),
        confirmNeeded = _io(j['confirm_needed']);

  final int? studentId;
  final String? studentCode;
  final String? fullName;
  final double confidence;
  final String status; // recognized | unknown | already_checked | spoof | confirming
  final String? evidenceImage;
  final double? livenessScore;
  final List<double>? bbox;
  final int? confirmCount;
  final int? confirmNeeded;
}

class SelfCheckinResult {
  SelfCheckinResult.fromJson(Json j)
      : status = _s(j['status']),
        confidence = _f(j['confidence']),
        livenessScore = _fo(j['liveness_score']),
        evidenceImage = _so(j['evidence_image']),
        recordId = _io(j['record_id']),
        recordStatus = _so(j['record_status']),
        message = _s(j['message']),
        distanceM = _fo(j['distance_m']),
        allowedRadiusM = _fo(j['allowed_radius_m']);

  final String status;
  final double confidence;
  final double? livenessScore;
  final String? evidenceImage;
  final int? recordId;
  final String? recordStatus;
  final String message;
  final double? distanceM;
  final double? allowedRadiusM;

  /// Bi chan vi vi tri (can bat dinh vi/ra gan khu vuc roi lay vi tri lai).
  bool get isLocationProblem =>
      const ['location_required', 'location_mocked', 'location_inaccurate', 'out_of_range'].contains(status);

  /// Ma QR thieu hoac het han - SV can quet lai ma dang chieu, khong phai chup lai anh.
  bool get isQrProblem => const ['qr_required', 'qr_invalid'].contains(status);
}

class SessionAttendance {
  SessionAttendance.fromJson(Json j)
      : sessionId = _i(j['session_id']),
        sessionDate = _date(j['session_date']),
        status = _so(j['status']),
        checkedAt = _dt(j['checked_at']),
        confidence = _fo(j['confidence']),
        evidenceImage = _so(j['evidence_image']),
        recordId = _io(j['record_id']),
        source = _so(j['source']),
        latitude = _fo(j['latitude']),
        longitude = _fo(j['longitude']),
        locationAccuracy = _fo(j['location_accuracy']),
        distanceM = _fo(j['distance_m']);

  final int sessionId;
  final DateTime sessionDate;
  final String? status;
  final DateTime? checkedAt;
  final double? confidence;
  final String? evidenceImage;
  final int? recordId;
  final String? source;
  final double? latitude;
  final double? longitude;
  final double? locationAccuracy;
  final double? distanceM;
}

class ClassAttendance {
  ClassAttendance.fromJson(Json j)
      : classId = _i(j['class_id']),
        classCode = _s(j['class_code']),
        subjectName = _s(j['subject_name']),
        semester = _s(j['semester']),
        lecturerName = _s(j['lecturer_name']),
        lecturerEmail = _s(j['lecturer_email']),
        present = _i(j['present']),
        late = _i(j['late']),
        absent = _i(j['absent']),
        excused = _i(j['excused']),
        manual = _i(j['manual']),
        totalSessions = _i(j['total_sessions']),
        absentRatio = _f(j['absent_ratio']),
        warnRatio = _f(j['warn_ratio']),
        warning = _b(j['warning']),
        sessions = _list(j['sessions'], SessionAttendance.fromJson);

  final int classId;
  final String classCode;
  final String subjectName;
  final String semester;
  final String lecturerName;
  final String lecturerEmail;
  final int present;
  final int late;
  final int absent;
  final int excused;
  final int manual;
  final int totalSessions;
  final double absentRatio;
  final double warnRatio;
  final bool warning;
  final List<SessionAttendance> sessions;
}

/// 1 dong thong ke chuyen can cua lop (GET /reports/attendance/{class_id}).
class ClassStatRow {
  ClassStatRow.fromJson(Json j)
      : studentId = _i(j['student_id']),
        studentCode = _s(j['student_code']),
        fullName = _s(j['full_name']),
        present = _i(j['present']),
        late = _i(j['late']),
        absent = _i(j['absent']),
        excused = _i(j['excused']),
        manual = _i(j['manual']),
        totalSessions = _i(j['total_sessions']),
        absentRatio = _f(j['absent_ratio']),
        warning = _b(j['warning']);

  final int studentId;
  final String studentCode;
  final String fullName;
  final int present;
  final int late;
  final int absent;
  final int excused;
  final int manual;
  final int totalSessions;
  final double absentRatio;
  final bool warning;
}

class CloseSummary {
  CloseSummary.fromJson(Json j)
      : absent = _i(j['absent']),
        present = _i(j['present']),
        newlyWarned = _list(j['newly_warned'], ClassStatRow.fromJson);

  final int absent;
  final int present;
  final List<ClassStatRow> newlyWarned;
}

class AuditEntry {
  AuditEntry.fromJson(Json j)
      : id = _i(j['id']),
        oldStatus = _s(j['old_status']),
        newStatus = _s(j['new_status']),
        reason = _s(j['reason']),
        changedAt = _dt(j['changed_at']);

  final int id;
  final String oldStatus;
  final String newStatus;
  final String reason;
  final DateTime? changedAt;
}

class RecordInfo {
  RecordInfo.fromJson(Json j)
      : id = _i(j['id']),
        studentId = _i(j['student_id']),
        status = _s(j['status']);

  final int id;
  final int studentId;
  final String status;
}

class ParentInfo {
  ParentInfo.fromJson(Json j)
      : id = _i(j['id']),
        fullName = _s(j['full_name']),
        email = _s(j['email']),
        phone = _s(j['phone']),
        childCount = _i(j['child_count']);

  final int id;
  final String fullName;
  final String email;
  final String phone;
  final int childCount;
}

class Unit {
  Unit.fromJson(Json j)
      : id = _i(j['id']),
        code = _s(j['code']),
        name = _s(j['name']),
        type = _s(j['type']);

  final int id;
  final String code;
  final String name;
  final String type;
}

class Location {
  Location.fromJson(Json j)
      : id = _i(j['id']),
        code = _s(j['code']),
        name = _s(j['name']),
        latitude = _f(j['latitude']),
        longitude = _f(j['longitude']),
        radiusM = _f(j['radius_m']),
        isDefault = _b(j['is_default']);

  final int id;
  final String code;
  final String name;
  final double latitude;
  final double longitude;
  final double radiusM;
  final bool isDefault;
}

/// Phong hoc trong danh muc. `effectiveRadiusM` la ban kinh thuc su duoc ap dung khi
/// doi chieu GPS - backend da nang len muc san neu phong co toa do rieng.
class Room {
  Room.fromJson(Json j)
      : id = _i(j['id']),
        code = _s(j['code']),
        name = _s(j['name']),
        locationId = _i(j['location_id']),
        locationName = _so(j['location_name']),
        building = _so(j['building']),
        floor = _io(j['floor']),
        capacity = _io(j['capacity']),
        latitude = _fo(j['latitude']),
        longitude = _fo(j['longitude']),
        radiusM = _fo(j['radius_m']),
        isActive = _b(j['is_active']),
        effectiveRadiusM = _fo(j['effective_radius_m']),
        scheduleCount = _i(j['schedule_count']);

  final int id;
  final String code;
  final String name;
  final int locationId;
  final String? locationName;
  final String? building;
  final int? floor;
  final int? capacity;
  final double? latitude;
  final double? longitude;
  final double? radiusM;
  final bool isActive;
  final double? effectiveRadiusM;
  final int scheduleCount;

  bool get hasOwnPoint => latitude != null && longitude != null;

  /// Dong mo ta ngan: toa nha, tang, suc chua - bo qua phan de trong.
  String get details => [
        if (building != null && building!.isNotEmpty) 'Nhà $building',
        if (floor != null) 'Tầng $floor',
        if (capacity != null) '$capacity chỗ',
      ].join(' · ');
}

class StaffMember {
  StaffMember.fromJson(Json j)
      : id = _i(j['id']),
        email = _s(j['email']),
        fullName = _s(j['full_name']),
        role = _s(j['role']),
        unitId = _i(j['unit_id']),
        unitCode = _s(j['unit_code']),
        unitName = _s(j['unit_name']),
        unitType = _s(j['unit_type']),
        position = _s(j['position']);

  final int id;
  final String email;
  final String fullName;
  final String role;
  final int unitId;
  final String unitCode;
  final String unitName;
  final String unitType;
  final String position;
}

class FacePending {
  FacePending.fromJson(Json j)
      : id = _i(j['id']),
        studentId = _i(j['student_id']),
        studentCode = _s(j['student_code']),
        fullName = _s(j['full_name']),
        sourceImage = _so(j['source_image']),
        createdAt = _dt(j['created_at']),
        duplicateWarning = _b(j['duplicate_warning']),
        duplicateStudentCode = _so(j['duplicate_student_code']),
        duplicateSimilarity = _fo(j['duplicate_similarity']);

  final int id;
  final int studentId;
  final String studentCode;
  final String fullName;
  final String? sourceImage;
  final DateTime? createdAt;
  final bool duplicateWarning;
  final String? duplicateStudentCode;
  final double? duplicateSimilarity;
}

class FaceMine {
  FaceMine.fromJson(Json j)
      : id = _i(j['id']),
        status = _s(j['status']),
        rejectReason = _s(j['reject_reason']),
        createdAt = _dt(j['created_at']);

  final int id;
  final String status;
  final String rejectReason;
  final DateTime? createdAt;
}

class OverviewStats {
  OverviewStats.fromJson(Json j)
      : classes = _i(j['classes']),
        students = _i(j['students']),
        lecturers = _i(j['lecturers']),
        closedSessions = _i(j['closed_sessions']),
        records = _i(j['records']),
        present = _i(j['present']),
        late = _i(j['late']),
        manual = _i(j['manual']),
        absent = _i(j['absent']),
        excused = _i(j['excused']),
        attendanceRate = _f(j['attendance_rate']),
        absentRate = _f(j['absent_rate']),
        warnedStudents = _i(j['warned_students']);

  final int classes;
  final int students;
  final int lecturers;
  final int closedSessions;
  final int records;
  final int present;
  final int late;
  final int manual;
  final int absent;
  final int excused;
  final double attendanceRate;
  final double absentRate;
  final int warnedStudents;
}

class OverviewFacultyRow extends OverviewStats {
  OverviewFacultyRow.fromJson(super.j)
      : facultyId = _io(j['faculty_id']),
        facultyCode = _so(j['faculty_code']),
        facultyName = _s(j['faculty_name']),
        super.fromJson();

  final int? facultyId;
  final String? facultyCode;
  final String facultyName;
}

class Overview {
  Overview.fromJson(Json j)
      : scope = _s(j['scope']),
        scopeName = _s(j['scope_name']),
        semester = _so(j['semester']),
        semesters = (j['semesters'] as List? ?? const []).map((e) => e.toString()).toList(),
        totals = OverviewStats.fromJson(j['totals'] as Json),
        byFaculty = _list(j['by_faculty'], OverviewFacultyRow.fromJson);

  final String scope;
  final String scopeName;
  final String? semester;
  final List<String> semesters;
  final OverviewStats totals;
  final List<OverviewFacultyRow> byFaculty;
}

/// Ma diem danh dang hieu luc cua mot phien - giang vien chieu len man hinh,
/// sinh vien quet (hoac go 6 chu so). Ma tu doi sau [rotateSeconds] giay.
class CheckinCode {
  CheckinCode.fromJson(Json j)
      : sessionId = _i(j['session_id']),
        qrPayload = _s(j['qr_payload']),
        digits = _s(j['digits']),
        rotateSeconds = _i(j['rotate_seconds']),
        expiresInSeconds = _i(j['expires_in_seconds']);

  final int sessionId;
  final String qrPayload;
  final String digits;
  final int rotateSeconds;
  final int expiresInSeconds;
}

/// Mot thong bao trong hop thu (hien dung cho phu huynh: con duoc ghi nhan diem danh).
class AppNotification {
  AppNotification.fromJson(Json j)
      : id = _i(j['id']),
        kind = _s(j['kind']),
        title = _s(j['title']),
        body = _s(j['body']),
        link = _so(j['link']),
        createdAt = _dt(j['created_at']),
        readAt = _dt(j['read_at']);

  final int id;
  final String kind;
  final String title;
  final String body;
  final String? link;
  final DateTime? createdAt;
  final DateTime? readAt;

  bool get isRead => readAt != null;
}

/// Tuy chon nhan thong bao cua phu huynh. [emailAvailable] = may chu da cau hinh gui email.
class ParentPreferences {
  ParentPreferences.fromJson(Json j)
      : notifyEmail = _b(j['notify_email']),
        notifyPresent = _b(j['notify_present']),
        emailAvailable = _b(j['email_available']);

  final bool notifyEmail;
  final bool notifyPresent;
  final bool emailAvailable;
}
