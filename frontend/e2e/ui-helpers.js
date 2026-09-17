/** Dang nhap qua form that (khong inject token thang vao sessionStorage) - dung
 * cho cac test can mo phong dung trai nghiem nguoi dung tu /login. */
export async function loginViaUi(page, email, password) {
  await page.goto('/login')
  await page.getByPlaceholder('ten@fams.edu.vn').fill(email)
  await page.getByPlaceholder('••••••••').fill(password)
  await page.getByRole('button', { name: /^đăng nhập$/i }).click()
  await page.waitForURL('/')
}
