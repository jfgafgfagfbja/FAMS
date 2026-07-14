import { describe, expect, it } from 'vitest'
import { getNavItems } from './nav'

describe('getNavItems', () => {
  it('gives students only their own attendance and enroll pages', () => {
    const items = getNavItems('student').map((i) => i.path)
    expect(items).toEqual(['/', '/enroll'])
  })

  it('does not expose a standalone session-opening attendance link to anyone', () => {
    // /attendance/:sessionId chi duoc vao qua nut "Mo phien diem danh" o dashboard,
    // khong co link tinh trong sidebar.
    expect(getNavItems('student').some((i) => i.path === '/attendance')).toBe(false)
    expect(getNavItems('lecturer').some((i) => i.path === '/attendance')).toBe(false)
    expect(getNavItems('admin').some((i) => i.path === '/attendance')).toBe(false)
  })

  it('gives lecturers the dashboard and enroll pages', () => {
    const items = getNavItems('lecturer').map((i) => i.path)
    expect(items).toEqual(['/', '/enroll'])
  })

  it('gives admins the lecturer nav plus student and class management', () => {
    const adminPaths = getNavItems('admin').map((i) => i.path)
    const lecturerPaths = getNavItems('lecturer').map((i) => i.path)
    expect(adminPaths).toEqual([...lecturerPaths, '/students', '/classes'])
  })
})
