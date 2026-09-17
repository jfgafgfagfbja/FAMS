import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { CalendarCheck, ClipboardText, WarningCircle, CalendarBlank, Camera, GraduationCap } from '@phosphor-icons/react'
import api from '../api'
import StatCard from '../components/StatCard'
import AttendanceDonut from '../components/AttendanceDonut'
import { todayBackendWeekday } from '../utils/format'

/** Trang chu sinh vien: the thong tin ca nhan + 3 o dem nhanh + tien do chuyen can tung lop. */
export default function StudentDashboard() {
  const [me, setMe] = useState(null)
  const [rows, setRows] = useState(null)
  const [todayCount, setTodayCount] = useState(0)

  useEffect(() => {
    let cancelled = false

    async function load() {
      const [{ data: meData }, { data: attendance }] = await Promise.all([
        api.get('/auth/me'),
        api.get('/reports/my-attendance'),
      ])
      if (cancelled) return
      setMe(meData)
      setRows(attendance)

      const todayWd = todayBackendWeekday()
      const perClass = await Promise.all(
        meData.classes.map(async (c) => {
          const { data: schedules } = await api.get(`/classes/${c.id}/schedules`)
          return schedules.filter((s) => s.weekday === todayWd).length
        }),
      )
      if (!cancelled) setTodayCount(perClass.reduce((a, b) => a + b, 0))
    }

    load()
    return () => {
      cancelled = true
    }
  }, [])

  if (!me || !rows) {
    return (
      <div>
        <div className="card skeleton" style={{ height: 100, marginBottom: 20 }} />
        <div className="stat-grid">
          {[0, 1, 2].map((i) => <div key={i} className="card stat-card skeleton" style={{ height: 112 }} />)}
        </div>
      </div>
    )
  }

  const totalAbsent = rows.reduce((sum, r) => sum + r.absent, 0)
  const warningCount = rows.filter((r) => r.warning).length
  const initials = me.full_name.split(' ').slice(-2).map((w) => w[0]).join('').toUpperCase()

  return (
    <div>
      <div className="card profile-card">
        <span className="profile-avatar">{initials}</span>
        <div className="profile-meta">
          <div className="profile-meta-item">
            <label>Họ và tên</label>
            <span>{me.full_name}</span>
          </div>
          <div className="profile-meta-item">
            <label>MSSV</label>
            <span>{me.student_code}</span>
          </div>
          <div className="profile-meta-item">
            <label>Ngành</label>
            <span>{me.major || '—'}</span>
          </div>
          <div className="profile-meta-item">
            <label>Khóa</label>
            <span>{me.cohort || '—'}</span>
          </div>
          <div className="profile-meta-item">
            <label>Lớp học phần</label>
            <span>{me.classes.map((c) => c.class_code).join(', ') || '—'}</span>
          </div>
        </div>
      </div>

      <div className="stat-grid stat-grid-3">
        <StatCard icon={CalendarCheck} label="Buổi học hôm nay" value={todayCount} tint="accent" to="/schedule" />
        <StatCard icon={ClipboardText} label="Buổi vắng học kỳ này" value={totalAbsent} tint="warning" to="/my-attendance" />
        <StatCard
          icon={WarningCircle}
          label="Lớp sắp vượt ngưỡng vắng"
          value={warningCount}
          tint={warningCount > 0 ? 'danger' : 'success'}
          to="/my-attendance"
        />
      </div>

      <div className="shortcut-grid">
        <Link to="/schedule" className="card shortcut-card">
          <span className="shortcut-icon"><CalendarBlank size={22} weight="bold" /></span>
          Lịch tuần
        </Link>
        <Link to="/my-attendance" className="card shortcut-card">
          <span className="shortcut-icon"><ClipboardText size={22} weight="bold" /></span>
          Chuyên cần
        </Link>
        <Link to="/enroll" className="card shortcut-card">
          <span className="shortcut-icon"><Camera size={22} weight="bold" /></span>
          Đăng ký khuôn mặt
        </Link>
      </div>

      <div className="dashboard-split">
        <div className="card" style={{ padding: 20 }}>
          <h3 style={{ marginTop: 0, fontSize: 15 }}>Tiến độ chuyên cần theo lớp</h3>
          {rows.length ? (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 24 }}>
              {rows.map((r) => (
                <div key={r.class_code} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8 }}>
                  <AttendanceDonut
                    present={r.total_sessions - r.absent}
                    total={r.total_sessions}
                    label="buổi có mặt"
                  />
                  <span style={{ fontSize: 12.5, fontWeight: 600, textAlign: 'center' }}>{r.class_code}</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-state">
              <ClipboardText size={32} />
              <p>Bạn chưa ghi danh lớp học phần nào nên chưa có dữ liệu chuyên cần.</p>
            </div>
          )}
        </div>

        <div className="card" style={{ padding: 20 }}>
          <h3 style={{ marginTop: 0, fontSize: 15 }}>Lớp học phần</h3>
          {me.classes.length ? (
            <div>
              {me.classes.map((c) => (
                <div key={c.id} className="class-list-row">
                  <div>
                    <div className="class-list-code">{c.class_code}</div>
                    <div className="class-list-subject">{c.subject_name}</div>
                  </div>
                  <span className="tag tag-neutral">{c.semester}</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-state">
              <GraduationCap size={28} />
              <p>Bạn chưa ghi danh lớp học phần nào.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
