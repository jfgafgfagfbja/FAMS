/// Vai tro va quyen phia giao dien - PHAN ANH ma tran quyen o backend (core/authz.py).
/// Backend van la noi kiem tra cuoi cung; o day chi de an/hien chuc nang cho dung.
class Roles {
  static const admin = 'admin';
  static const lecturer = 'lecturer';
  static const student = 'student';
  static const parent = 'parent';
  static const training = 'training_office';
  static const affairs = 'student_affairs';
  static const faculty = 'faculty_office';
  static const board = 'board';

  static const staff = [training, affairs, faculty, board];

  static bool isStaff(String role) => staff.contains(role);

  static String label(String role) => switch (role) {
        admin => 'Quản trị viên',
        lecturer => 'Giảng viên',
        student => 'Sinh viên',
        parent => 'Phụ huynh',
        training => 'Phòng Đào tạo',
        affairs => 'Phòng Công tác sinh viên',
        faculty => 'Văn phòng Khoa',
        board => 'Ban ngành',
        _ => role,
      };
}

class Perms {
  Perms(this.role);

  final String role;

  bool _in(List<String> roles) => roles.contains(role);

  /// Lop hoc phan, lich hoc, ghi danh, ho so giang vien.
  bool get manageAcademic => _in(const [Roles.admin, Roles.training]);

  /// Ho so SV, phu huynh, duyet khuon mat, xac nhan dong y ho.
  bool get manageStudents => _in(const [Roles.admin, Roles.affairs]);

  bool get viewStudents => _in(const [Roles.admin, Roles.training, Roles.affairs, Roles.faculty]);
  bool get viewLecturers => _in(const [Roles.admin, Roles.training, Roles.faculty]);
  bool get viewParents => _in(const [Roles.admin, Roles.affairs, Roles.training]);
  bool get viewClasses => _in(const [Roles.admin, Roles.training, Roles.affairs, Roles.faculty, Roles.lecturer]);
  bool get viewSessions => viewClasses;
  bool get viewReports => viewClasses;
  bool get viewOverview => _in(const [Roles.admin, Roles.training, Roles.affairs, Roles.faculty, Roles.board]);
  bool get reviewFaces => manageStudents;
  bool get manageUnits => role == Roles.admin;

  /// Mo phien, quet camera, xac nhan tay, sua moi trang thai (GV chi lop minh day).
  bool get operateAttendance => _in(const [Roles.admin, Roles.lecturer]);

  /// Duyet "Co phep" / huy duyet (P.CTSV toan truong, Khoa trong pham vi Khoa).
  bool get excuseOnly => _in(const [Roles.affairs, Roles.faculty]);

  bool get editAttendance => operateAttendance || excuseOnly;

  /// Dang ky khuon mat ho SV (GV chi SV lop minh day).
  bool get enrollFaceForOthers => _in(const [Roles.admin, Roles.affairs, Roles.lecturer]);
}
