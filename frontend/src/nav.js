import { House, CalendarCheck, Camera, ClipboardText } from '@phosphor-icons/react'

export function getNavItems(role) {
  if (role === 'student') {
    return [
      { path: '/', label: 'Điểm danh của tôi', icon: ClipboardText },
      { path: '/enroll', label: 'Đăng ký khuôn mặt', icon: Camera },
    ]
  }
  return [
    { path: '/', label: 'Dashboard', icon: House },
    { path: '/attendance', label: 'Điểm danh', icon: CalendarCheck },
    { path: '/enroll', label: 'Đăng ký khuôn mặt', icon: Camera },
  ]
}
