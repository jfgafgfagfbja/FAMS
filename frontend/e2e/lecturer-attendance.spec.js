import { test, expect } from '@playwright/test'
import { createIsolatedClass, getCachedAdminToken, waitForLoginRateLimitWindow } from './api-helpers.js'
import { loginViaUi } from './ui-helpers.js'

test.describe('Giang vien: mo phien -> xac nhan tay -> dong phien', () => {
  let fixture

  test.beforeAll(async ({ request }) => {
    const adminToken = getCachedAdminToken()
    // lecturer_code/student_code gioi han VARCHAR(20) o DB - chi lay 9 chu so cuoi
    // cua timestamp (E2EGV + 9 = 14 ky tu, an toan), van du duy nhat cho tung lan chay.
    fixture = await createIsolatedClass(request, adminToken, Date.now().toString().slice(-9))
  })

  test('mo phien tu dashboard, xac nhan tay 1 SV, dong phien va modal tong ket dung so lieu', async ({ page }) => {
    await waitForLoginRateLimitWindow()
    await loginViaUi(page, fixture.lecturer.email, fixture.lecturer.password)

    await expect(page.getByRole('heading', { name: /lịch dạy hôm nay/i })).toBeVisible()
    await page.getByRole('button', { name: /mở phiên điểm danh/i }).click()

    await page.waitForURL(/\/attendance\/\d+/)
    await expect(page.getByText(fixture.clazz.class_code)).toBeVisible()

    // xac nhan tay cho SV duy nhat trong roster
    await page.getByRole('button', { name: /xác nhận tay/i }).click()
    await expect(page.getByText(fixture.student.full_name)).toBeVisible()
    await expect(page.locator('.roster-row', { hasText: fixture.student.full_name })
      .locator('.tag')).toHaveText(/điểm danh tay/i)

    // dong phien - window.confirm() phai duoc chap nhan truoc khi bam
    page.once('dialog', (dialog) => dialog.accept())
    await page.getByRole('button', { name: /^đóng phiên$/i }).click()

    await expect(page.getByRole('heading', { name: /đã đóng phiên điểm danh/i })).toBeVisible()
    const summaryGrid = page.locator('.modal-summary-grid')
    await expect(summaryGrid.locator('div').nth(0).locator('.modal-summary-value')).toHaveText('1') // Co mat
    await expect(summaryGrid.locator('div').nth(1).locator('.modal-summary-value')).toHaveText('0') // Vang
  })
})
