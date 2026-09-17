import { defineConfig, devices } from '@playwright/test'

// Tro toi stack docker compose dang chay (frontend:5173 qua nginx, backend:8000
// truc tiep cho cac API helper tao du lieu). Doi qua bien moi truong khi can
// chay o moi truong khac (vd CI dung port khac).
const BASE_URL = process.env.E2E_BASE_URL || 'http://localhost:5173'
export const API_URL = process.env.E2E_API_URL || 'http://localhost:8000'

export default defineConfig({
  testDir: './e2e',
  globalSetup: './e2e/global-setup.js',
  // 100s: du cho truong hop mot so file phai cho toi ~65s de tranh dung rate
  // limit dang nhap that (xem waitForLoginRateLimitWindow trong api-helpers.js).
  timeout: 100_000,
  expect: { timeout: 10_000 },
  fullyParallel: false, // cac test tao du lieu that qua API tren cung 1 DB dung chung
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: process.env.CI ? [['list'], ['html', { open: 'never' }]] : 'list',

  use: {
    baseURL: BASE_URL,
    trace: 'retain-on-failure',
    video: 'retain-on-failure',
    // Webcam gia: khong can camera that. Dung dong thoi launch args (Chromium
    // tra ve 1 video gia lien tuc cho getUserMedia) + grant quyen truoc, de
    // AttendanceScreen/EnrollFace render duoc video ma khong bi cham quyen truy cap.
    permissions: ['camera', 'microphone'],
    launchOptions: {
      args: [
        '--use-fake-device-for-media-stream',
        '--use-fake-ui-for-media-stream',
      ],
    },
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
})
