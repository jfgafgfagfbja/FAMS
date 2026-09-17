import { Fragment, useEffect, useState } from 'react'
import { WarningCircle, ClipboardText, EnvelopeSimple, MapPin } from '@phosphor-icons/react'
import api from '../api'
import { API_BASE_URL } from '../config'
import { formatSemester, parseSemesterLabel } from '../utils/format'

const STATUS_LABEL = {
  present: 'Có mặt', late: 'Muộn', absent: 'Vắng', manual: 'Có mặt (tay)', excused: 'Có phép',
}
const STATUS_TINT = {
  present: 'success', late: 'warning', absent: 'danger', manual: 'success', excused: 'neutral',
}
const SOURCE_LABEL = { camera: 'Camera lớp học', selfie: 'Tự chụp (selfie)', manual: 'GV xác nhận tay' }

function absencesUntilBanned(row) {
  if (!row.total_sessions) return 0
  return Math.max(Math.ceil(row.warn_ratio * row.total_sessions) - row.absent, 0)
}

function disputeMailto(me, row, session) {
  const subject = `Khieu nai diem danh - ${row.class_code} - ${session.session_date}`
  const body = `Kính gửi thầy/cô ${row.lecturer_name},\n\n`
    + `Em là ${me.full_name} (MSSV ${me.student_code}), xin khiếu nại kết quả điểm danh `
    + `buổi ${session.session_date} - lớp ${row.class_code} (${row.subject_name}).\n`
    + `Hệ thống đang ghi nhận: ${STATUS_LABEL[session.status] || 'chưa điểm danh'}.\n\n`
    + `Lý do khiếu nại: \n\nEm cảm ơn thầy/cô.`
  return `mailto:${row.lecturer_email}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`
}

/** Trang chuyen can SV: dropdown hoc ky + bang chi tiet (mo rong tung buoi) + bieu do cot. */
export default function MyAttendance() {
  const [me, setMe] = useState(null)
  const [semester, setSemester] = useState(null)
  const [rows, setRows] = useState(null)
  const [expandedId, setExpandedId] = useState(null)

  useEffect(() => {
    api.get('/auth/me').then(({ data }) => {
      setMe(data)
      const options = [...new Set(data.classes.map((c) => c.semester))].sort().reverse()
      setSemester(options[0] || null)
    })
  }, [])

  useEffect(() => {
    if (!semester) return undefined
    let cancelled = false
    setRows(null)
    api.get('/students/me/attendance', { params: { semester } }).then(({ data }) => {
      if (!cancelled) setRows(data)
    })
    return () => {
      cancelled = true
    }
  }, [semester])

  if (!me) {
    return <div className="card skeleton" style={{ height: 300 }} />
  }

  if (!me.classes.length) {
    return (
      <div className="card empty-state">
        <ClipboardText size={32} />
        <p>Bạn chưa được ghi danh vào lớp học phần nào.</p>
      </div>
    )
  }

  const semesterOptions = [...new Set(me.classes.map((c) => c.semester))].sort().reverse()

  return (
    <div>
      <div className="card" style={{ marginBottom: 20 }}>
        <div
          style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            padding: '18px 20px 4px', flexWrap: 'wrap', gap: 12,
          }}
        >
          <h3 style={{ margin: 0, fontSize: 15 }}>Kết quả chuyên cần</h3>
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
                  <th>Chuyên cần</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => {
                  const absentPct = r.total_sessions ? Math.round(r.absent_ratio * 1000) / 10 : 0
                  const preWarnRatio = 0.8 * r.warn_ratio
                  const isPreWarning = r.total_sessions > 0 && r.absent_ratio >= preWarnRatio
                  const attendPct = r.total_sessions ? Math.round((1 - r.absent_ratio) * 100) : 100
                  const barColor = r.warning ? 'var(--danger)' : isPreWarning ? 'var(--warning)' : 'var(--success)'
                  const n = absencesUntilBanned(r)

                  return (
                    <Fragment key={r.class_id}>
                      <tr
                        className={`row-clickable${isPreWarning ? ' row-warning' : ''}`}
                        onClick={() => setExpandedId((id) => (id === r.class_id ? null : r.class_id))}
                      >
                        <td>
                          {isPreWarning && (
                            <WarningCircle
                              size={14} weight="fill" color="var(--danger)"
                              style={{ verticalAlign: -2, marginRight: 4 }}
                              title={r.warning
                                ? 'Đã vượt ngưỡng cấm thi'
                                : `Vắng thêm ${n} buổi sẽ bị cấm thi`}
                            />
                          )}
                          {r.class_code} — {r.subject_name}
                        </td>
                        <td>{r.present + r.manual}</td>
                        <td>{r.late}</td>
                        <td>{r.absent}</td>
                        <td>{r.excused}</td>
                        <td>{r.total_sessions ? `${absentPct}%` : '—'}</td>
                        <td>
                          <div className="mini-progress">
                            <div className="mini-progress-fill" style={{ width: `${attendPct}%`, background: barColor }} />
                          </div>
                        </td>
                      </tr>
                      {expandedId === r.class_id && (
                        <tr className="attendance-detail-row">
                          <td colSpan={7}>
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
                                      <th></th>
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
                                              <MapPin size={13} /> Bản đồ
                                            </a>
                                          ) : '—'}
                                        </td>
                                        <td>
                                          <a
                                            href={disputeMailto(me, r, s)}
                                            className="btn btn-ghost"
                                            style={{ padding: '5px 10px', fontSize: 12 }}
                                            onClick={(e) => e.stopPropagation()}
                                          >
                                            <EnvelopeSimple size={13} /> Khiếu nại
                                          </a>
                                        </td>
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                              ) : (
                                <p style={{ margin: 0, fontSize: 13, color: 'var(--text-muted)' }}>
                                  Chưa có buổi học nào. Mở phiên điểm danh để bắt đầu.
                                </p>
                              )}
                            </div>
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {rows && rows.length > 0 && (
        <div className="card" style={{ padding: 20 }}>
          <h3 style={{ margin: '0 0 4px', fontSize: 15 }}>% chuyên cần theo học kỳ</h3>
          <p style={{ margin: '2px 0 0', color: 'var(--text-muted)', fontSize: 13 }}>{formatSemester(semester)}</p>
          <div className="semester-barchart">
            {rows.map((r) => {
              const attendPct = r.total_sessions ? Math.round((1 - r.absent_ratio) * 100) : 0
              const preWarnRatio = 0.8 * r.warn_ratio
              const color = r.warning ? 'var(--danger)' : r.absent_ratio >= preWarnRatio ? 'var(--warning)' : 'var(--success)'
              return (
                <div key={r.class_id} className="semester-bar-col">
                  <span className="semester-bar-value">{attendPct}%</span>
                  <div className="semester-bar" style={{ height: `${attendPct}%`, background: color }} />
                  <span className="semester-bar-label">{r.class_code}</span>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
