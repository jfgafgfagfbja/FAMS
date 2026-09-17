import {
  House, CalendarBlank, ClipboardText, Camera, Users, GraduationCap,
  ChalkboardTeacher, ChartBar, FingerprintSimple, UsersThree,
} from '@phosphor-icons/react'

export function getNavItems(role) {
  if (role === 'student') {
    return [
      { path: '/', label: 'Trang chủ', icon: House },
      { path: '/schedule', label: 'Lịch học', icon: CalendarBlank },
      { path: '/my-attendance', label: 'Chuyên cần của tôi', icon: ClipboardText },
      { path: '/enroll', label: 'Đăng ký khuôn mặt', icon: Camera },
    ]
  }

  if (role === 'parent') {
    return [
      { path: '/', label: 'Con em của tôi', icon: UsersThree },
    ]
  }

  if (role === 'lecturer') {
    return [
      { path: '/', label: 'Trang chủ', icon: House },
      { path: '/schedule', label: 'Lịch dạy', icon: CalendarBlank },
      { path: '/sessions', label: 'Phiên điểm danh', icon: ClipboardText },
      { path: '/reports', label: 'Báo cáo chuyên cần', icon: ChartBar },
    ]
  }

  return [
    { path: '/', label: 'Trang chủ', icon: House },
    { path: '/admin/students', label: 'Sinh viên', icon: Users },
    { path: '/admin/lecturers', label: 'Giảng viên', icon: ChalkboardTeacher },
    { path: '/admin/classes', label: 'Lớp học phần', icon: GraduationCap },
    { path: '/admin/schedules', label: 'Lịch học', icon: CalendarBlank },
    { path: '/face-review', label: 'Duyệt khuôn mặt', icon: FingerprintSimple },
    { path: '/admin/parents', label: 'Phụ huynh', icon: UsersThree },
  ]
}
