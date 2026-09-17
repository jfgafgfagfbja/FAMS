/** Ho tro tao du lieu that qua API cho tung test (khong dung du lieu seed chung,
 * tranh cac test anh huong lan nhau khi chay tren cung 1 DB that cua stack docker). */
import fs from 'node:fs'
import { API_URL } from '../playwright.config.js'
import { AUTH_CACHE_PATH } from './global-setup.js'

/** Token admin dang nhap 1 lan duy nhat o globalSetup - dung cho MOI thao tac tao
 * du lieu qua API thay vi tung file/test tu dang nhap rieng (xem global-setup.js). */
export function getCachedAdminToken() {
  return JSON.parse(fs.readFileSync(AUTH_CACHE_PATH, 'utf-8')).adminToken
}

/**
 * /auth/login gioi han 5 lan/phut/IP (co chu dich, chong brute-force - xem
 * backend/app/api/auth.py). Cum dang nhap dau tien cua suite (globalSetup +
 * admin.spec.js + auth.spec.js, ~6 lan) da dung gan/het han muc trong vai giay
 * dau. Cac file can dang nhap UI THEM (giang vien, sinh vien) phai doi den khi
 * qua han 1 phut ke tu lan dang nhap dau tien, tranh bi 429 do dung do voi cum
 * tren - day la danh doi co chu dich (suite cham hon vai chuc giay) de TON TRONG
 * rate limit that cua production thay vi noi long no chi de test chay nhanh hon.
 */
export async function waitForLoginRateLimitWindow() {
  const { firstLoginAt } = JSON.parse(fs.readFileSync(AUTH_CACHE_PATH, 'utf-8'))
  const elapsed = Date.now() - firstLoginAt
  const remaining = 65_000 - elapsed // 65s = 60s cua so + 5s bien an toan
  if (remaining > 0) {
    await new Promise((resolve) => setTimeout(resolve, remaining))
  }
}

export async function apiLogin(request, email, password) {
  const resp = await request.post(`${API_URL}/auth/login`, {
    form: { username: email, password },
  })
  if (!resp.ok()) {
    throw new Error(`Dang nhap that bai (${resp.status()}): ${await resp.text()}`)
  }
  return (await resp.json()).access_token
}

function authHeaders(token) {
  return { Authorization: `Bearer ${token}` }
}

/** Thu 2=0 .. CN=6, giong quy uoc backend (trung voi Python date.weekday()). */
function todayBackendWeekday() {
  return (new Date().getDay() + 6) % 7
}

/** "YYYY-MM-DD" theo GIO DIA PHUONG - KHONG dung toISOString() (luon tra ve UTC,
 * co the lech 1 ngay so voi "hom nay" that o cac mui gio truoc UTC nhu VN/+7). */
function todayLocalDate() {
  const d = new Date()
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function hhmmss(d) {
  return d.toTimeString().slice(0, 8)
}

/** Khung gio lich hoc "dang mo duoc ngay bay gio": open_session chi cho mo phien
 * trong [start - EARLY_OPEN_MINUTES, end] cua dung ngay hom nay, nen lich test
 * phai bat dau ~10 phut nua (nam trong khung mo som) va ket thuc ~3 tieng nua.
 * Clamp ve cuoi ngay de gio khong trao nguoc khi suite chay sat nua dem. */
function openableScheduleWindow() {
  const now = new Date()
  const startDt = new Date(now.getTime() + 10 * 60_000)
  const endDt = new Date(now.getTime() + 3 * 3_600_000)
  return {
    start_time: startDt.getDate() === now.getDate() ? hhmmss(startDt) : '23:58:00',
    end_time: endDt.getDate() === now.getDate() ? hhmmss(endDt) : '23:59:59',
  }
}

/**
 * Tao 1 bo du lieu doc lap qua API: 1 giang vien + 1 sinh vien + 1 lop hoc phan
 * + 1 lich hoc (thu = hom nay, de hien ra o "Lich day hom nay") + ghi danh SV
 * vao lop. Dung suffix duy nhat (vd Date.now()) de khong dung voi lan chay khac.
 */
export async function createIsolatedClass(request, adminToken, suffix) {
  const headers = authHeaders(adminToken)
  const lecturerEmail = `e2e-gv-${suffix}@fams.edu.vn`
  const studentEmail = `e2e-sv-${suffix}@fams.edu.vn`
  const password = 'e2epass123'

  const lecturerResp = await request.post(`${API_URL}/lecturers`, {
    headers,
    data: {
      email: lecturerEmail, password,
      full_name: `E2E Giang Vien ${suffix}`, lecturer_code: `E2EGV${suffix}`, department: 'E2E',
    },
  })
  if (!lecturerResp.ok()) throw new Error(`Tao giang vien loi: ${await lecturerResp.text()}`)
  // LecturerOut khong tra ve email/password nen phai tu luu lai (dung khi dang nhap qua UI)
  const lecturer = { ...(await lecturerResp.json()), email: lecturerEmail, password }

  const studentResp = await request.post(`${API_URL}/students`, {
    headers,
    data: {
      email: studentEmail, password,
      full_name: `E2E Sinh Vien ${suffix}`, student_code: `E2ESV${suffix}`, major: 'CNTT', cohort: 2026,
    },
  })
  if (!studentResp.ok()) throw new Error(`Tao sinh vien loi: ${await studentResp.text()}`)
  const student = { ...(await studentResp.json()), email: studentEmail, password }

  const classResp = await request.post(`${API_URL}/classes`, {
    headers,
    data: {
      class_code: `E2E${suffix}`, subject_name: 'Mon hoc E2E',
      lecturer_id: lecturer.id, semester: '2026.1',
    },
  })
  if (!classResp.ok()) throw new Error(`Tao lop loi: ${await classResp.text()}`)
  const clazz = await classResp.json()

  const scheduleResp = await request.post(`${API_URL}/classes/schedules`, {
    headers,
    data: {
      class_id: clazz.id, weekday: todayBackendWeekday(),
      ...openableScheduleWindow(), room: 'E2E-101',
    },
  })
  if (!scheduleResp.ok()) throw new Error(`Tao lich hoc loi: ${await scheduleResp.text()}`)
  const schedule = await scheduleResp.json()

  const enrollResp = await request.post(`${API_URL}/classes/${clazz.id}/enroll/${student.id}`, { headers })
  if (!enrollResp.ok()) throw new Error(`Ghi danh loi: ${await enrollResp.text()}`)

  return { lecturer, student, clazz, schedule }
}

/** Mo phien -> xac nhan tay SV -> dong phien, hoan toan qua API (dung khi test
 * chi can DU LIEU da diem danh san, khong can kiem tra luong UI diem danh).
 * Nhan token bat ky co quyen "lecturer" hoac "admin" (ensure_class_access cho
 * phep admin thao tac moi lop) - dung token admin da cache de khong phai dang
 * nhap them 1 tai khoan giang vien rieng, giu tong so lan goi /auth/login thap. */
export async function runAttendanceCycleViaApi(request, token, scheduleId, studentId) {
  const headers = authHeaders(token)
  const today = todayLocalDate()

  const openResp = await request.post(`${API_URL}/sessions`, {
    headers, data: { schedule_id: scheduleId, session_date: today },
  })
  if (!openResp.ok()) throw new Error(`Mo phien loi: ${await openResp.text()}`)
  const session = await openResp.json()

  const manualResp = await request.post(`${API_URL}/sessions/${session.id}/manual`, {
    headers, data: { student_id: studentId },
  })
  if (!manualResp.ok()) throw new Error(`Xac nhan tay loi: ${await manualResp.text()}`)

  const closeResp = await request.patch(`${API_URL}/sessions/${session.id}/close`, { headers })
  if (!closeResp.ok()) throw new Error(`Dong phien loi: ${await closeResp.text()}`)

  return session
}
