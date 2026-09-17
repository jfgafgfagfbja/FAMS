import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { MapPin } from '@phosphor-icons/react'
import api from '../api'
import { API_BASE_URL } from '../config'

// Backend chi cho sua sang 4 trang thai nay (manual chi tao qua nut xac nhan tay).
const STATUS_OPTIONS = ['present', 'late', 'absent', 'excused']
const STATUS_LABEL = { present: 'Có mặt', late: 'Muộn', absent: 'Vắng', excused: 'Có phép', manual: 'Điểm danh tay' }
const SOURCE_LABEL = { camera: 'Camera lớp học', selfie: 'SV tự chụp', manual: 'Xác nhận tay' }

/** Xem va sua record diem danh sau buoi hoc. */
export default function SessionRecords() {
  const { sessionId } = useParams()
  const [session, setSession] = useState(null)
  const [roster, setRoster] = useState(null)
  const [records, setRecords] = useState([])
  const [savingId, setSavingId] = useState(null)

  const load = async () => {
    const { data: s } = await api.get(`/sessions/${sessionId}`)
    setSession(s)
    const [{ data: students }, { data: recs }] = await Promise.all([
      api.get(`/classes/${s.class_id}/students`),
      api.get(`/sessions/${sessionId}/records`),
    ])
    setRoster(students)
    setRecords(recs)
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId])

  const updateStatus = async (recordId, status) => {
    // Backend bat buoc ly do cho moi lan sua (luu vao nhat ky attendance_audits).
    const reason = window.prompt('Lý do sửa trạng thái điểm danh (bắt buộc):')
    if (!reason || !reason.trim()) return
    setSavingId(recordId)
    try {
      await api.patch(`/sessions/${sessionId}/records/${recordId}`, { status, reason: reason.trim() })
      await load()
    } catch (err) {
      alert(err.response?.data?.detail || 'Không sửa được trạng thái điểm danh.')
    } finally {
      setSavingId(null)
    }
  }

  const markManual = async (studentId) => {
    try {
      await api.post(`/sessions/${sessionId}/manual`, { student_id: studentId })
      await load()
    } catch (err) {
      alert(err.response?.data?.detail || 'Không xác nhận được.')
    }
  }

  if (!session || !roster) {
    return <div className="card skeleton" style={{ height: 300 }} />
  }

  const recordByStudent = new Map(records.map((r) => [r.student_id, r]))

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <h2 style={{ margin: 0 }}>{session.class_code} — {session.subject_name}</h2>
        <p style={{ margin: '2px 0 0', color: 'var(--text-muted)', fontSize: 13.5 }}>
          Phòng {session.room} · {session.session_date} · Trạng thái phiên: {session.status === 'open' ? 'Đang mở' : 'Đã đóng'}
        </p>
      </div>

      <div className="card">
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>MSSV</th>
                <th>Họ tên</th>
                <th>Trạng thái</th>
                <th>Độ tin cậy</th>
                <th>Nguồn</th>
                <th>Ảnh bằng chứng</th>
                <th>Vị trí</th>
                <th>Giờ ghi nhận</th>
              </tr>
            </thead>
            <tbody>
              {roster.map((s) => {
                const record = recordByStudent.get(s.id)
                return (
                  <tr key={s.id}>
                    <td>{s.student_code}</td>
                    <td>{s.full_name}</td>
                    <td>
                      {record ? (
                        <select
                          className="select"
                          value={record.status}
                          disabled={savingId === record.id}
                          onChange={(e) => updateStatus(record.id, e.target.value)}
                        >
                          {!STATUS_OPTIONS.includes(record.status) && (
                            <option value={record.status} disabled>{STATUS_LABEL[record.status] || record.status}</option>
                          )}
                          {STATUS_OPTIONS.map((opt) => (
                            <option key={opt} value={opt}>{STATUS_LABEL[opt]}</option>
                          ))}
                        </select>
                      ) : session.status === 'open' ? (
                        <button className="btn btn-ghost" onClick={() => markManual(s.id)}>
                          Đánh dấu có mặt (tay)
                        </button>
                      ) : '—'}
                    </td>
                    <td>{record ? record.confidence : '—'}</td>
                    <td>{record ? SOURCE_LABEL[record.source] || record.source : '—'}</td>
                    <td>
                      {record?.evidence_image ? (
                        <img
                          src={`${API_BASE_URL}${record.evidence_image}`}
                          width={44}
                          height={44}
                          style={{ objectFit: 'cover', borderRadius: 8, border: '1px solid var(--border)' }}
                          alt={`Ảnh bằng chứng của ${s.full_name}`}
                        />
                      ) : (
                        '—'
                      )}
                    </td>
                    <td>
                      {record?.latitude != null && record?.longitude != null ? (
                        <a
                          href={`https://www.google.com/maps?q=${record.latitude},${record.longitude}`}
                          target="_blank"
                          rel="noreferrer"
                          className="btn btn-ghost"
                          style={{ padding: '5px 10px', fontSize: 12 }}
                        >
                          <MapPin size={13} /> Bản đồ
                        </a>
                      ) : '—'}
                    </td>
                    <td>{record ? new Date(record.checked_at).toLocaleTimeString() : '—'}</td>
                  </tr>
                )
              })}
              {!roster.length && (
                <tr>
                  <td colSpan={8} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 24 }}>
                    Lớp này chưa có sinh viên ghi danh
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
