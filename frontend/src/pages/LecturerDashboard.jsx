import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  Clock, MapPin, CalendarCheck, ClipboardText, WarningCircle,
  CalendarBlank, ChartBar,
} from '@phosphor-icons/react'
import api from '../api'
import StatCard from '../components/StatCard'
import { formatSemester } from '../utils/format'

/** Dashboard giang vien: the dem nhanh + lich day hom nay + mo phien diem danh + shortcut. */
export default function LecturerDashboard() {
  const navigate = useNavigate()
  const [me, setMe] = useState(null)
  const [todaySchedules, setTodaySchedules] = useState(null)
  const [openCount, setOpenCount] = useState(0)
  const [warningCount, setWarningCount] = useState(0)
  const [opening, setOpening] = useState(null)

  useEffect(() => {
    let cancelled = false

    async function load() {
      const [{ data: meData }, { data: today }, { data: openSessions }] = await Promise.all([
        api.get('/auth/me'),
        api.get('/lecturers/me/today-schedules'),
        api.get('/sessions', { params: { status: 'open', mine: true } }),
      ])
      if (cancelled) return
      setMe(meData)
      setTodaySchedules(today)
      setOpenCount(openSessions.length)

      const warningLists = await Promise.all(
        meData.classes.map(async (c) => {
          try {
            const { data } = await api.get('/reports/attendance/warnings', { params: { class_id: c.id } })
            return data.map((r) => r.student_id)
          } catch {
            return []
          }
        }),
      )
      if (!cancelled) setWarningCount(new Set(warningLists.flat()).size)
    }

    load()
    return () => {
      cancelled = true
    }
  }, [])

  const openSession = async (scheduleId) => {
    setOpening(scheduleId)
    try {
      const { data } = await api.post('/sessions', {
        schedule_id: scheduleId,
        session_date: new Date().toISOString().slice(0, 10),
      })
      navigate(`/attendance/${data.id}`)
    } finally {
      setOpening(null)
    }
  }

  if (!me || !todaySchedules) {
    return (
      <div>
        <div className="stat-grid stat-grid-3">
          {[0, 1, 2].map((i) => <div key={i} className="card stat-card skeleton" style={{ height: 112 }} />)}
        </div>
        <div className="card skeleton" style={{ height: 200 }} />
      </div>
    )
  }

  return (
    <div>
      <div className="stat-grid stat-grid-3">
        <StatCard icon={CalendarCheck} label="Buổi dạy hôm nay" value={todaySchedules.length} tint="accent" to="/schedule" />
        <StatCard icon={ClipboardText} label="Phiên đang mở" value={openCount} tint="accent" to="/sessions" />
        <StatCard
          icon={WarningCircle}
          label="SV vượt ngưỡng vắng"
          value={warningCount}
          tint={warningCount > 0 ? 'danger' : 'success'}
          to="/reports"
        />
      </div>

      <div className="shortcut-grid">
        <Link to="/schedule" className="card shortcut-card">
          <span className="shortcut-icon"><CalendarBlank size={22} weight="bold" /></span>
          Lịch dạy
        </Link>
        <Link to="/reports" className="card shortcut-card">
          <span className="shortcut-icon"><ChartBar size={22} weight="bold" /></span>
          Báo cáo
        </Link>
        <Link to="/sessions" className="card shortcut-card">
          <span className="shortcut-icon"><ClipboardText size={22} weight="bold" /></span>
          Phiên đang mở
        </Link>
      </div>

      <div className="card" style={{ padding: 20, marginBottom: 20 }}>
        <h3 style={{ marginTop: 0, fontSize: 15 }}>Lịch dạy hôm nay</h3>
        {todaySchedules.length ? (
          <div style={{ display: 'grid', gap: 4 }}>
            {todaySchedules.map((s) => (
              <div
                key={s.schedule_id}
                style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  padding: '12px 0', borderBottom: '1px solid var(--border)',
                }}
              >
                <div>
                  <strong>{s.class_code}</strong> — {s.subject_name}
                  <div style={{ fontSize: 12.5, color: 'var(--text-muted)', marginTop: 2 }}>
                    <Clock size={13} style={{ verticalAlign: -2 }} /> {s.start_time}–{s.end_time}
                    {'   '}
                    <MapPin size={13} style={{ verticalAlign: -2 }} /> Phòng {s.room}
                  </div>
                </div>
                <button
                  className="btn btn-primary"
                  onClick={() => openSession(s.schedule_id)}
                  disabled={opening === s.schedule_id}
                >
                  {opening === s.schedule_id ? 'Đang mở…' : 'Mở phiên điểm danh'}
                </button>
              </div>
            ))}
          </div>
        ) : (
          <div className="empty-state">
            <CalendarBlank size={28} />
            <p>Hôm nay không có lịch dạy.</p>
          </div>
        )}
      </div>

      <div className="card">
        <h3 style={{ margin: 0, padding: '16px 16px 8px', fontSize: 15 }}>Lớp của tôi</h3>
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Mã lớp</th>
                <th>Môn học</th>
                <th>Học kỳ</th>
              </tr>
            </thead>
            <tbody>
              {me.classes.map((c) => (
                <tr key={c.id}>
                  <td>{c.class_code}</td>
                  <td>{c.subject_name}</td>
                  <td>{formatSemester(c.semester)}</td>
                </tr>
              ))}
              {!me.classes.length && (
                <tr>
                  <td colSpan={3} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 24 }}>
                    Chưa được phân công lớp học phần nào
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
