import { Fragment, useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ClipboardText, MapPin, WarningCircle } from '@phosphor-icons/react'
import api from '../api'
import { API_BASE_URL } from '../config'
import { formatSemester, parseSemesterLabel } from '../utils/format'

const STATUS_LABEL = {
  present: 'Có mặt', late: 'Muộn', absent: 'Vắng', manual: 'Có mặt (tay)', excused: 'Có phép',
}
const STATUS_TINT = {
  present: 'success', late: 'warning', absent: 'danger', manual: 'success', excused: 'neutral',
}
const SOURCE_LABEL = { camera: 'Camera lớp học', selfie: 'SV tự chụp', manual: 'GV xác nhận tay' }

/** Phu huynh xem chuyen can 1 con: giong bo cuc MyAttendance.jsx cua SV nhung
 * chi doc (khong co nut khieu nai), kem cot "Nguon" va "Vi tri" (link Google Maps)
 * khi buoi do SV tu diem danh bang selfie kem GPS. */
export default function ParentChildAttendance() {
  const { studentId } = useParams()
  const navigate = useNavigate()
  const [child, setChild] = useState(null)
  const [semester, setSemester] = useState(null)
  const [rows, setRows] = useState(null)
  const [expandedId, setExpandedId] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.get('/parents/me/children')
      .then(({ data }) => {
        const found = data.find((c) => String(c.id) === String(studentId))
        if (!found) {
          navigate('/')
          return
        }
        setChild(found)
        const options = [...new Set(found.classes.map((c) => c.semester))].sort().reverse()
        setSemester(options[0] || null)
      })
      .catch((err) => setError(err.response?.data?.detail || 'Không tải được thông tin con em.'))
  }, [studentId, navigate])

  useEffect(() => {
    if (!semester) return undefined
    let cancelled = false
    setRows(null)
    api.get(`/parents/me/children/${studentId}/attendance`, { params: { semester } })
      .then(({ data }) => {
        if (!cancelled) setRows(data)
      })
      .catch((err) => {
        if (!cancelled) setError(err.response?.data?.detail || 'Không tải được dữ liệu chuyên cần.')
      })
    return () => {
      cancelled = true
    }
  }, [studentId, semester])

  if (error) {
    return (
      <div className="card empty-state">
        <WarningCircle size={32} />
        <p>{error}</p>
      </div>
    )
  }

  if (!child) {
    return <div className="card skeleton" style={{ height: 300 }} />
  }

  if (!child.classes.length) {
    return (
      <div className="card empty-state">
        <ClipboardText size={32} />
        <p>{child.full_name} chưa được ghi danh vào lớp học phần nào.</p>
      </div>
    )
  }

  const semesterOptions = [...new Set(child.classes.map((c) => c.semester))].sort().reverse()

  return (
    <div>
      <p style={{ margin: '0 0 12px', fontSize: 13.5, color: 'var(--text-muted)' }}>
        <Link to="/" style={{ color: 'inherit' }}>Con em của tôi</Link> / {child.full_name} ({child.student_code})
      </p>

      <div className="card">
        <div
          style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            padding: '18px 20px 4px', flexWrap: 'wrap', gap: 12,
          }}
        >
          <h3 style={{ margin: 0, fontSize: 15 }}>Kết quả chuyên cần — {child.full_name}</h3>
          <select
            className="select"
            value={formatSemester(semester)}
            onChange={(e) => { setExpandedId(null); setSemester(parseSemesterLabel(e.target.value)) }}
          >
            {semesterOptions.map((s) => (
              <option key={s} value={formatSemester(s)}>{formatSemester(s)}</option>
            ))}
          </select>
        </div>

        {rows === null ? (
          <div style={{ padding: 20 }}>
            <div className="skeleton" style={{ height: 120, borderRadius: 8 }} />
          </div>
        ) : !rows.length ? (
          <div className="empty-state">
            <ClipboardText size={32} />
            <p>Chưa có buổi điểm danh nào được đóng trong học kỳ này.</p>
          </div>
        ) : (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Lớp học phần</th>
                  <th>Có mặt</th>
                  <th>Muộn</th>
                  <th>Vắng</th>
                  <th>Có phép</th>
                  <th>% vắng</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <Fragment key={r.class_id}>
                    <tr
                      className="row-clickable"
                      onClick={() => setExpandedId((id) => (id === r.class_id ? null : r.class_id))}
                    >
                      <td>{r.class_code} — {r.subject_name}</td>
                      <td>{r.present + r.manual}</td>
                      <td>{r.late}</td>
                      <td>{r.absent}</td>
                      <td>{r.excused}</td>
                      <td>{r.total_sessions ? `${Math.round(r.absent_ratio * 1000) / 10}%` : '—'}</td>
                    </tr>
                    {expandedId === r.class_id && (
                      <tr className="attendance-detail-row">
                        <td colSpan={6}>
                          <div className="attendance-detail-inner">
                            {r.sessions.length ? (
                              <table className="data-table">
                                <thead>
                                  <tr>
                                    <th>Ngày</th>
                                    <th>Trạng thái</th>
                                    <th>Giờ ghi nhận</th>
                                    <th>Nguồn</th>
                                    <th>Ảnh bằng chứng</th>
                                    <th>Vị trí</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {r.sessions.map((s) => (
                                    <tr key={s.session_id}>
                                      <td>{s.session_date}</td>
                                      <td>
                                        <span className={`tag tag-${STATUS_TINT[s.status] || 'neutral'}`}>
                                          {STATUS_LABEL[s.status] || 'Chưa điểm danh'}
                                        </span>
                                      </td>
                                      <td>{s.checked_at ? new Date(s.checked_at).toLocaleTimeString() : '—'}</td>
                                      <td>{s.source ? SOURCE_LABEL[s.source] || s.source : '—'}</td>
                                      <td>
                                        {s.evidence_image ? (
                                          <img
                                            src={`${API_BASE_URL}${s.evidence_image}`}
                                            width={40} height={40}
                                            style={{ objectFit: 'cover', borderRadius: 8, border: '1px solid var(--border)' }}
                                            alt={`Bằng chứng điểm danh ngày ${s.session_date}`}
                                          />
                                        ) : '—'}
                                      </td>
                                      <td>
                                        {s.latitude != null && s.longitude != null ? (
                                          <a
                                            href={`https://www.google.com/maps?q=${s.latitude},${s.longitude}`}
                                            target="_blank"
                                            rel="noreferrer"
                                            className="btn btn-ghost"
                                            style={{ padding: '5px 10px', fontSize: 12 }}
                                            onClick={(e) => e.stopPropagation()}
                                          >
                                            <MapPin size={13} /> Xem bản đồ
                                          </a>
                                        ) : '—'}
                                      </td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            ) : (
                              <p style={{ margin: 0, fontSize: 13, color: 'var(--text-muted)' }}>
                                Chưa có buổi học nào trong học kỳ này.
                              </p>
                            )}
                          </div>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
