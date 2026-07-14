import { useEffect, useState } from 'react'
import api from '../api'

/** Sinh vien tu xem lich su diem danh cua minh theo tung lop da dang ky. */
export default function MyAttendance() {
  const [rows, setRows] = useState(null)

  useEffect(() => {
    api.get('/reports/my-attendance').then(({ data }) => setRows(data))
  }, [])

  if (rows === null) {
    return <div className="card skeleton" style={{ height: 200 }} />
  }

  if (!rows.length) {
    return (
      <div className="card empty-state">
        <p>Bạn chưa được ghi danh vào lớp học phần nào.</p>
      </div>
    )
  }

  return (
    <div className="card">
      <div className="table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              <th>Lớp học phần</th>
              <th>Có mặt</th>
              <th>Muộn</th>
              <th>Vắng</th>
              <th>Tổng buổi</th>
              <th>Trạng thái</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.class_code}>
                <td>
                  {r.class_code} — {r.subject_name}
                </td>
                <td>{r.present + r.manual}</td>
                <td>{r.late}</td>
                <td>{r.absent}</td>
                <td>{r.total_sessions}</td>
                <td>
                  {r.warning ? (
                    <span className="tag tag-warning">Nguy cơ cấm thi</span>
                  ) : (
                    <span className="tag tag-success">Bình thường</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
