import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Clock, MapPin } from '@phosphor-icons/react'
import api from '../api'

const WEEKDAYS = ['Thứ 2', 'Thứ 3', 'Thứ 4', 'Thứ 5', 'Thứ 6', 'Thứ 7', 'Chủ nhật']

/** Chuyen doi thu JS (0=CN..6=T7) sang quy uoc backend (0=T2..6=CN). */
function todayBackendWeekday() {
  const jsDay = new Date().getDay()
  return (jsDay + 6) % 7
}

/** Dashboard giang vien: lop minh day + lich day hom nay + mo phien diem danh. */
export default function LecturerDashboard() {
  const navigate = useNavigate()
  const [classes, setClasses] = useState(null)
  const [todaySchedules, setTodaySchedules] = useState([])
  const [opening, setOpening] = useState(null)

  useEffect(() => {
    let cancelled = false

    async function load() {
      const { data: myClasses } = await api.get('/classes', { params: { mine: true } })
      if (cancelled) return
      setClasses(myClasses)

      const todayWd = todayBackendWeekday()
      const entries = await Promise.all(
        myClasses.map(async (c) => {
          const { data: schedules } = await api.get(`/classes/${c.id}/schedules`)
          return schedules
            .filter((s) => s.weekday === todayWd)
            .map((s) => ({ ...s, class_code: c.class_code, subject_name: c.subject_name }))
        }),
      )
      if (!cancelled) setTodaySchedules(entries.flat())
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

  if (classes === null) {
    return <div className="card skeleton" style={{ height: 200 }} />
  }

  return (
    <div>
      <div className="card" style={{ padding: 20, marginBottom: 20 }}>
        <h3 style={{ marginTop: 0, fontSize: 15 }}>Lịch dạy hôm nay</h3>
        {todaySchedules.length ? (
          <div style={{ display: 'grid', gap: 4 }}>
            {todaySchedules.map((s) => (
              <div
                key={s.id}
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
                  onClick={() => openSession(s.id)}
                  disabled={opening === s.id}
                >
                  {opening === s.id ? 'Đang mở…' : 'Mở phiên điểm danh'}
                </button>
              </div>
            ))}
          </div>
        ) : (
          <p style={{ color: 'var(--text-muted)', fontSize: 13.5, margin: 0 }}>
            Hôm nay ({WEEKDAYS[todayBackendWeekday()]}) không có lịch dạy.
          </p>
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
              {classes.map((c) => (
                <tr key={c.id}>
                  <td>{c.class_code}</td>
                  <td>{c.subject_name}</td>
                  <td>{c.semester}</td>
                </tr>
              ))}
              {!classes.length && (
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
