import { test, expect } from '@playwright/test'
import { createIsolatedClass, getCachedAdminToken, runAttendanceCycleViaApi, waitForLoginRateLimitWindow } from './api-helpers.js'
import { loginViaUi } from './ui-helpers.js'

// Dung chung 1 phien dang nhap SV cho ca 2 test trong file nay (thay vi dang nhap
// lai tu dau moi test) - giam so lan goi that /auth/login (gioi han 5 lan/phut/IP).
test.describe.configure({ mode: 'serial' })

test.describe('Sinh vien: lich tuan va chuyen can hien dung du lieu vua diem danh', () => {
  let fixture
  let page

  test.beforeAll(async ({ browser, request }) => {
    const adminToken = getCachedAdminToken()
    // lecturer_code/student_code gioi han VARCHAR(20) o DB - chi lay 9 chu so cuoi
    // cua timestamp (E2EGV + 9 = 14 ky tu, an toan), van du duy nhat cho tung lan chay.
    fixture = await createIsolatedClass(request, adminToken, Date.now().toString().slice(-9))
    await runAttendanceCycleViaApi(request, adminToken, fixture.schedule.id, fixture.student.id)

    await waitForLoginRateLimitWindow()
    page = await browser.newPage()
    await loginViaUi(page, fixture.student.email, fixture.student.password)
  })

  test.afterAll(async () => {
    await page.close()
  })

  test('lich tuan hien badge Co mat cho buoi vua diem danh', async () => {
    await page.getByRole('link', { name: /lịch học/i }).click()
    await page.waitForURL('/schedule')

    const slot = page.locator('.timetable-slot', { hasText: fixture.clazz.class_code })
    await expect(slot).toBeVisible()
    await expect(slot.locator('.timetable-slot-badge')).toHaveText(/có mặt/i)
  })

  test('trang chuyen can hien dung so buoi co mat cua lop vua diem danh', async () => {
    await page.getByRole('link', { name: /chuyên cần của tôi/i }).click()
    await page.waitForURL('/my-attendance')

    const row = page.locator('tr', { hasText: fixture.clazz.class_code })
    await expect(row).toBeVisible()
    const cells = row.locator('td')
    await expect(cells.nth(1)).toHaveText('1') // Co mat (manual tinh la co mat)
    await expect(cells.nth(2)).toHaveText('0') // Muon
    await expect(cells.nth(3)).toHaveText('0') // Vang
  })
})
