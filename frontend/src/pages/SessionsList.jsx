import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ClipboardText } from '@phosphor-icons/react'
import api from '../api'

const role = sessionStorage.getItem('role')

/** Danh sach phien diem danh: dang mo (vao tiep tuc) va da dong gan day (xem lai record). */
export default function SessionsList() {
  const [sessions, setSessions] = useState(null)

  useEffect(() => {
    api.get('/sessions', { params: { mine: role === 'lecturer' } }).then(({ data }) => setSessions(data))
  }, [])

  if (sessions === null) {
    return <div className="card skeleton" style={{ height: 240 }} />
  }

  const open = sessions.filter((s) => s.status === 'open')
  const closed = sessions.filter((s) => s.status === 'closed').slice(0, 20)

  return (
    <div>
      <div className="card" style={{ marginBottom: 20 }}>
        <h3 style={{ margin: 0, padding: '16px 16px 8px', fontSize: 15 }}>Đang mở</h3>
        {open.length ? (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Mã lớp</th>
                  <th>Môn học</th>
                  <th>Ngày</th>
                  <th>Phòng</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {open.map((s) => (
                  <tr key={s.id}>
                    <td>{s.class_code}</td>
                    <td>{s.subject_name}</td>
                    <td>{s.session_date}</td>
                    <td>{s.room}</td>
                    <td>
                      <Link to={`/attendance/${s.id}`} className="btn btn-primary">Tiếp tục điểm danh</Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="empty-state">
            <ClipboardText size={28} />
            <p>Không có phiên nào đang mở. Mở phiên mới từ trang chủ.</p>
          </div>
        )}
      </div>

      <div className="card">
        <h3 style={{ margin: 0, padding: '16px 16px 8px', fontSize: 15 }}>Đã đóng gần đây</h3>
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Mã lớp</th>
                <th>Môn học</th>
                <th>Ngày</th>
                <th>Phòng</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {closed.map((s) => (
                <tr key={s.id}>
                  <td>{s.class_code}</td>
                  <td>{s.subject_name}</td>
                  <td>{s.session_date}</td>
                  <td>{s.room}</td>
                  <td>
                    <Link to={`/sessions/${s.id}/records`} className="btn btn-ghost">Xem kết quả</Link>
                  </td>
                </tr>
              ))}
              {!closed.length && (
                <tr>
                  <td colSpan={5} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 24 }}>
                    Chưa có phiên nào đã đóng
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
