import { test, expect } from '@playwright/test'
import { loginViaUi } from './ui-helpers.js'

// Dung chung 1 phien dang nhap admin cho ca 2 test (giam so lan goi that
// /auth/login - gioi han 5 lan/phut/IP).
test.describe.configure({ mode: 'serial' })

test.describe('Admin: CRUD sinh vien co ban va trang duyet khuon mat', () => {
  let page

  test.beforeAll(async ({ browser }) => {
    page = await browser.newPage()
    await loginViaUi(page, 'admin@fams.edu.vn', 'admin123')
  })

  test.afterAll(async () => {
    await page.close()
  })

  test('them, sua, xoa 1 sinh vien', async () => {
    // student_code gioi han VARCHAR(20) o DB - E2EADM (6) + 9 chu so = 15, an toan
    const suffix = Date.now().toString().slice(-9)
    const studentCode = `E2EADM${suffix}`
    const email = `e2e-admin-sv-${suffix}@fams.edu.vn`

    await page.getByRole('link', { name: /^sinh viên$/i }).click()
    await page.waitForURL('/admin/students')

    await page.getByRole('button', { name: /thêm mới/i }).click()
    await page.getByLabel('Email').fill(email)
    await page.getByLabel('Mật khẩu').fill('e2epass123')
    await page.getByLabel('Họ tên').fill(`E2E Admin Test ${suffix}`)
    await page.getByLabel('MSSV').fill(studentCode)
    await page.getByLabel('Ngành').fill('CNTT')
    await page.getByLabel('Khóa').fill('2026')
    await page.getByRole('button', { name: /^lưu$/i }).click()

    await expect(page.getByRole('heading', { name: /thêm sinh viên mới/i })).toBeHidden()

    // loc theo MSSV vua tao de tim dung dong bat ke phan trang
    await page.locator('.admin-toolbar-search input').fill(studentCode)
    const row = page.locator('tr', { hasText: studentCode })
    await expect(row).toBeVisible()

    // sua: doi nganh
    await row.getByLabel('Sửa').click()
    await page.getByLabel('Ngành').fill('Khoa hoc may tinh')
    await page.getByRole('button', { name: /^lưu$/i }).click()
    await expect(page.locator('tr', { hasText: studentCode })).toContainText('Khoa hoc may tinh')

    // xoa: xac nhan dialog
    page.once('dialog', (dialog) => dialog.accept())
    await page.locator('tr', { hasText: studentCode }).getByLabel('Xóa').click()
    await expect(page.locator('tr', { hasText: studentCode })).toHaveCount(0)
  })

  test('trang duyet khuon mat mo duoc', async () => {
    await page.getByRole('link', { name: /duyệt khuôn mặt/i }).click()
    await page.waitForURL('/face-review')
    await expect(
      page.getByText(/chờ duyệt|không có yêu cầu/i).first(),
    ).toBeVisible()
  })
})
