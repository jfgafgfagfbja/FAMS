import { describe, expect, it } from 'vitest'
import { getNavItems } from './nav'

describe('getNavItems', () => {
  it('gives students their own study menu', () => {
    const items = getNavItems('student').map((i) => i.path)
    expect(items).toEqual(['/', '/schedule', '/my-attendance', '/enroll'])
  })

  it('does not expose a standalone session-opening attendance link to anyone', () => {
    // /attendance/:sessionId chi duoc vao qua nut "Mo phien diem danh" o dashboard,
    // khong co link tinh trong sidebar.
    expect(getNavItems('student').some((i) => i.path === '/attendance')).toBe(false)
    expect(getNavItems('lecturer').some((i) => i.path === '/attendance')).toBe(false)
    expect(getNavItems('admin').some((i) => i.path === '/attendance')).toBe(false)
  })

  it('gives lecturers the teaching-focused menu', () => {
    const items = getNavItems('lecturer').map((i) => i.path)
    expect(items).toEqual(['/', '/schedule', '/sessions', '/reports'])
  })

  it('gives admins student/lecturer/class/schedule management plus face review', () => {
    const adminPaths = getNavItems('admin').map((i) => i.path)
    expect(adminPaths).toEqual([
      '/', '/admin/students', '/admin/lecturers', '/admin/classes', '/admin/schedules', '/face-review',
    ])
  })
})
