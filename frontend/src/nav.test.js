import { describe, expect, it } from 'vitest'
import { getNavItems } from './nav'

describe('getNavItems', () => {
  it('gives students only their own attendance and enroll pages', () => {
    const items = getNavItems('student').map((i) => i.path)
    expect(items).toEqual(['/', '/enroll'])
  })

  it('does not expose the session-opening attendance screen to students', () => {
    const items = getNavItems('student').map((i) => i.path)
    expect(items).not.toContain('/attendance')
  })

  it('gives lecturers the dashboard, attendance, and enroll pages', () => {
    const items = getNavItems('lecturer').map((i) => i.path)
    expect(items).toEqual(['/', '/attendance', '/enroll'])
  })

  it('gives admins the lecturer nav plus student and class management', () => {
    const adminPaths = getNavItems('admin').map((i) => i.path)
    const lecturerPaths = getNavItems('lecturer').map((i) => i.path)
    expect(adminPaths).toEqual([...lecturerPaths, '/students', '/classes'])
  })
})
