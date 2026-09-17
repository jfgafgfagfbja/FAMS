/**
 * Dang nhap admin DUY NHAT 1 LAN cho ca luot chay E2E, luu token ra file tam.
 * Ly do: /auth/login gioi han 5 lan/phut/IP (co chu dich, chong brute-force) -
 * neu moi test file/tu tu goi apiLogin(admin) rieng, tong so lan dang nhap that
 * trong toan bo suite se vuot nguong va bi 429 (khong phai loi ung dung, ma la
 * xung dot giua toc do chay test voi rate limit). Cache 1 token dung chung cho
 * moi thao tac tao du lieu qua API giam so lan dang nhap that xuong toi thieu.
 */
import { request as playwrightRequest } from '@playwright/test'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { API_URL } from '../playwright.config.js'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
export const AUTH_CACHE_PATH = path.join(__dirname, '.auth-cache.json')

export default async function globalSetup() {
  const ctx = await playwrightRequest.newContext()
  const resp = await ctx.post(`${API_URL}/auth/login`, {
    form: { username: 'admin@fams.edu.vn', password: 'admin123' },
  })
  if (!resp.ok()) {
    throw new Error(`Global setup: dang nhap admin that bai (${resp.status()}): ${await resp.text()}`)
  }
  const { access_token } = await resp.json()
  // Luu lai moc thoi gian cua lan dang nhap DAU TIEN trong ca suite - cac file
  // test can dang nhap UI rieng (GV, SV) se doi den khi qua han cua so rate
  // limit (xem waitForLoginRateLimitWindow trong api-helpers.js) truoc khi dang
  // nhap, tranh dung do voi cum dang nhap dau (admin.spec + auth.spec).
  fs.writeFileSync(AUTH_CACHE_PATH, JSON.stringify({
    adminToken: access_token, firstLoginAt: Date.now(),
  }))
  await ctx.dispose()
}
