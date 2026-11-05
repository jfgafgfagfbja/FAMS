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
  static const facultyLeader = 'faculty_leader';
  static const board = 'board';

  static const staff = [training, affairs, faculty, facultyLeader, board];

  /// Hai vai tro cua Khoa: chi thay du lieu trong Khoa minh.
  static const facultyRoles = [faculty, facultyLeader];

  static bool isStaff(String role) => staff.contains(role);

  static bool isFaculty(String role) => facultyRoles.contains(role);

  static String label(String role) => switch (role) {
        admin => 'Quản trị viên',
        lecturer => 'Giảng viên',
        student => 'Sinh viên',
        parent => 'Phụ huynh',
        training => 'Phòng Đào tạo',
        affairs => 'Phòng Công tác sinh viên',
        faculty => 'Văn phòng Khoa',
        facultyLeader => 'Lãnh đạo Khoa',
        board => 'Ban ngành',
        _ => role,
      };

  /// Nhiem vu cua tung nhom tren he thong - hien o trang Tai khoan de nguoi dung biet minh
  /// duoc lam gi. Giu khop voi ma tran quyen o backend/app/core/authz.py.
  static List<String> duties(String role) => switch (role) {
        admin => const [
            'Quản lý tài khoản cán bộ, đơn vị và toàn bộ danh mục',
            'Đặt lại mật khẩu cho mọi tài khoản',
            'Mở phiên, sửa kết quả điểm danh mọi lớp',
            'Xem nhật ký hệ thống toàn trường',
          ],
        training => const [
            'Lớp học phần, lịch học, ghi danh, phân công giảng viên (toàn trường)',
            'Hồ sơ giảng viên, phòng học, địa điểm điểm danh',
            'Xem điểm danh, báo cáo, cảnh báo vắng toàn trường',
          ],
        affairs => const [
            'Hồ sơ sinh viên, phụ huynh, ghi nhận đồng ý sinh trắc học',
            'Đặt lại mật khẩu cho sinh viên, phụ huynh',
            'Duyệt ảnh khuôn mặt sinh viên',
            'Duyệt vắng có phép toàn trường',
            'Xem điểm danh, báo cáo, cảnh báo vắng toàn trường',
          ],
        faculty => const [
            'Nhập liệu của Khoa: lớp học phần, lịch học, ghi danh, phân công giảng viên',
            'Xem sinh viên, giảng viên, điểm danh và báo cáo trong Khoa',
          ],
        facultyLeader => const [
            'Giám sát điểm danh, báo cáo, cảnh báo vắng của Khoa',
            'Duyệt vắng có phép cho sinh viên trong Khoa',
            'Xem nhật ký thao tác liên quan đến Khoa',
            'Không nhập liệu - việc này do Văn phòng Khoa đảm nhận',
          ],
        board => const ['Xem thống kê tổng hợp toàn trường (không có tên, ảnh sinh viên)'],
        lecturer => const [
            'Mở phiên, quét camera, chiếu mã QR điểm danh cho lớp mình dạy',
            'Xác nhận tay và sửa kết quả điểm danh lớp mình dạy',
          ],
        student => const [
            'Tự điểm danh bằng khuôn mặt hoặc mã QR, xem chuyên cần của mình',
            'Đồng ý hoặc rút đồng ý sử dụng dữ liệu khuôn mặt',
          ],
        parent => const ['Xem chuyên cần và nhận thông báo điểm danh của con'],
        _ => const [],
      };
}

class Perms {
  Perms(this.role);

  final String role;

  bool _in(List<String> roles) => roles.contains(role);

  /// Ho so giang vien, phong hoc, dia diem diem danh (toan truong).
  bool get manageAcademic => _in(const [Roles.admin, Roles.training]);

  /// Lop hoc phan, lich hoc, ghi danh, phan cong GV day lop. Van phong Khoa chi trong Khoa
  /// minh - danh sach lop ho thay da gioi han san theo Khoa.
  bool get editClasses => _in(const [Roles.admin, Roles.training, Roles.faculty]);

  /// Ho so SV, phu huynh, duyet khuon mat, xac nhan dong y ho.
  bool get manageStudents => _in(const [Roles.admin, Roles.affairs]);

  bool get viewStudents => _in(const [Roles.admin, Roles.training, Roles.affairs, ...Roles.facultyRoles]);
  bool get viewLecturers => _in(const [Roles.admin, Roles.training, ...Roles.facultyRoles]);
  bool get viewParents => _in(const [Roles.admin, Roles.affairs, Roles.training]);
  bool get viewClasses =>
      _in(const [Roles.admin, Roles.training, Roles.affairs, ...Roles.facultyRoles, Roles.lecturer]);
  bool get viewSessions => viewClasses;
  bool get viewReports => viewClasses;
  bool get viewOverview =>
      _in(const [Roles.admin, Roles.training, Roles.affairs, ...Roles.facultyRoles, Roles.board]);
  bool get reviewFaces => manageStudents;
  bool get manageUnits => role == Roles.admin;

  /// Dat lai mat khau cho nguoi khac: admin moi tai khoan, P.CTSV cho SV va phu huynh.
  bool get resetStudentPassword => manageStudents;
  bool get resetStaffPassword => role == Roles.admin;

  /// Nhat ky he thong: admin toan truong, Lanh dao Khoa trong Khoa minh.
  bool get viewAuditLog => _in(const [Roles.admin, Roles.facultyLeader]);

  /// Dia diem diem danh (toa do + ban kinh doi chieu GPS) - cung nhom quan ly hoc vu.
  bool get manageLocations => manageAcademic;

  /// Mo phien, quet camera, xac nhan tay, sua moi trang thai (GV chi lop minh day).
  bool get operateAttendance => _in(const [Roles.admin, Roles.lecturer]);

  /// Chi duyet / huy duyet "Co phep" (P.CTSV toan truong, Lanh dao Khoa trong Khoa minh).
  bool get approveExcuse => _in(const [Roles.affairs, Roles.facultyLeader]);

  bool get editAttendance => operateAttendance || approveExcuse;

  /// Dang ky khuon mat ho SV (GV chi SV lop minh day).
  bool get enrollFaceForOthers => _in(const [Roles.admin, Roles.affairs, Roles.lecturer]);
}
