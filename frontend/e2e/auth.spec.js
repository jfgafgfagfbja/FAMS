import { test, expect } from '@playwright/test'
import { loginViaUi } from './ui-helpers.js'

test.describe('Dang nhap', () => {
  test('sai mat khau hien thong bao loi ro rang', async ({ page }) => {
    await page.goto('/login')
    await page.getByPlaceholder('ten@fams.edu.vn').fill('admin@fams.edu.vn')
    await page.getByPlaceholder('••••••••').fill('sai-mat-khau-chac-chan')
    await page.getByRole('button', { name: /^đăng nhập$/i }).click()

    await expect(page.getByText(/sai email hoặc mật khẩu/i)).toBeVisible()
    await expect(page).toHaveURL(/\/login$/)
  })

  test('admin dang nhap dung vao dung dashboard', async ({ page }) => {
    await loginViaUi(page, 'admin@fams.edu.vn', 'admin123')
    await expect(page.getByText(/tổng sinh viên/i)).toBeVisible()
  })

  test('giang vien dang nhap dung vao dashboard giang vien', async ({ page }) => {
    await loginViaUi(page, 'gv01@fams.edu.vn', 'gv123')
    await expect(page.getByRole('heading', { name: /lịch dạy hôm nay/i })).toBeVisible()
  })

  test('sinh vien dang nhap dung vao dashboard sinh vien', async ({ page }) => {
    await loginViaUi(page, 'sv01@fams.edu.vn', 'sv123')
    await expect(page.getByText(/họ và tên/i)).toBeVisible()
  })
})
