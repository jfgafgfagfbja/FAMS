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

  it('gives admins the same nav as lecturers', () => {
    expect(getNavItems('admin')).toEqual(getNavItems('lecturer'))
  })
})
