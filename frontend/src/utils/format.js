/** Chuyen "2026.1" (YYYY.N luu trong Class.semester) sang "HK1 - 2026-2027". */
export function formatSemester(semester) {
  const m = /^(\d{4})\.(\d)$/.exec(semester || '')
  if (!m) return semester
  const year = Number(m[1])
  return `HK${m[2]} - ${year}-${year + 1}`
}

/** Chieu nguoc cua formatSemester: "HK1 - 2026-2027" -> "2026.1" (dang luu o backend). */
export function parseSemesterLabel(label) {
  const m = /^HK(\d)\s*-\s*(\d{4})-(\d{4})$/.exec((label || '').trim())
  if (!m) return label
  return `${m[2]}.${m[1]}`
}

/** Sinh danh sach hoc ky (HK1/2/3) tu (nam hien tai - yearsBack) den (+ yearsForward),
 * dang raw "YYYY.N" de dung lam value dropdown - hien thi qua formatSemester. */
export function generateSemesterOptions(yearsBack = 1, yearsForward = 1) {
  const now = new Date().getFullYear()
  const options = []
  for (let y = now + yearsForward; y >= now - yearsBack; y--) {
    for (let term = 3; term >= 1; term--) {
      options.push(`${y}.${term}`)
    }
  }
  return options
}

export const WEEKDAYS = ['Thứ 2', 'Thứ 3', 'Thứ 4', 'Thứ 5', 'Thứ 6', 'Thứ 7', 'Chủ nhật']

/** Chuyen doi thu JS (0=CN..6=T7) sang quy uoc backend (0=T2..6=CN). */
export function todayBackendWeekday() {
  const jsDay = new Date().getDay()
  return (jsDay + 6) % 7
}

/** Format date thanh "YYYY-MM-DD" theo gio dia phuong (tranh lech ngay do toISOString dung UTC). */
export function toISODate(d) {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

/** Thu 2 cua tuan chua ngay d (quy uoc weekday 0=T2..6=CN giong backend). */
export function toMonday(d) {
  const jsDay = d.getDay()
  const diff = (jsDay + 6) % 7
  const monday = new Date(d)
  monday.setDate(d.getDate() - diff)
  monday.setHours(0, 0, 0, 0)
  return monday
}

export function addDays(d, n) {
  const copy = new Date(d)
  copy.setDate(d.getDate() + n)
  return copy
}

/** Format "dd/MM/yyyy". */
export function formatDDMMYYYY(d) {
  const day = String(d.getDate()).padStart(2, '0')
  const m = String(d.getMonth() + 1).padStart(2, '0')
  return `${day}/${m}/${d.getFullYear()}`
}
