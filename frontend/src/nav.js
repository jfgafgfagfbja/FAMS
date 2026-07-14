import { House, Camera, ClipboardText, Users, GraduationCap } from '@phosphor-icons/react'

export function getNavItems(role) {
  if (role === 'student') {
    return [
      { path: '/', label: 'Điểm danh của tôi', icon: ClipboardText },
      { path: '/enroll', label: 'Đăng ký khuôn mặt', icon: Camera },
    ]
  }

  const items = [
    { path: '/', label: 'Dashboard', icon: House },
    { path: '/enroll', label: 'Đăng ký khuôn mặt', icon: Camera },
  ]

  if (role === 'admin') {
    items.push(
      { path: '/students', label: 'Sinh viên', icon: Users },
      { path: '/classes', label: 'Lớp học phần', icon: GraduationCap },
    )
  }

  return items
}
