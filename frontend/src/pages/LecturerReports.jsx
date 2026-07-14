import { useEffect, useState } from 'react'
import { DownloadSimple, ChartBar } from '@phosphor-icons/react'
import api from '../api'
import { formatSemester } from '../utils/format'

/** Bao cao chuyen can cho giang vien: chon lop -> bang thong ke + xuat Excel. */
export default function LecturerReports() {
  const [classes, setClasses] = useState(null)
  const [selectedId, setSelectedId] = useState(null)
  const [rows, setRows] = useState(null)
  const [exporting, setExporting] = useState(false)

  useEffect(() => {
    api.get('/auth/me').then(({ data }) => {
      setClasses(data.classes)
      if (data.classes.length) setSelectedId(data.classes[0].id)
    })
  }, [])

  useEffect(() => {
    if (!selectedId) return
    let cancelled = false
    setRows(null)
    api.get(`/reports/attendance/${selectedId}`).then(({ data }) => {
      if (!cancelled) setRows(data)
    })
    return () => {
      cancelled = true
    }
  }, [selectedId])

  const selectedClass = classes?.find((c) => c.id === selectedId)

  const exportExcel = async () => {
    if (!selectedClass) return
    setExporting(true)
    try {
      const { data } = await api.get('/reports/attendance/export', {
        params: { class_id: selectedClass.id, semester: selectedClass.semester },
        responseType: 'blob',
      })
      const url = URL.createObjectURL(data)
      const a = document.createElement('a')
      a.href = url
      a.download = `diemdanh_${selectedClass.class_code}_${selectedClass.semester}.xlsx`
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
    } catch {
      alert('Không xuất được báo cáo. Lớp có thể chưa có buổi điểm danh nào đã đóng.')
    } finally {
      setExporting(false)
    }
  }

  if (classes === null) {
    return <div className="card skeleton" style={{ height: 300 }} />
  }

  if (!classes.length) {
    return (
      <div className="card empty-state">
        <ChartBar size={32} />
        <p>Bạn chưa được phân công lớp học phần nào nên chưa có báo cáo.</p>
      </div>
    )
  }

  return (
    <div className="card">
      <div
        style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: 20, paddingBottom: 16, flexWrap: 'wrap', gap: 12,
        }}
      >
        <div>
          <h3 style={{ margin: 0, fontSize: 15 }}>Chuyên cần theo lớp</h3>
          {selectedClass && (
            <p style={{ margin: '2px 0 0', color: 'var(--text-muted)', fontSize: 13 }}>
              {formatSemester(selectedClass.semester)}
            </p>
          )}
        </div>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          <select className="select" value={selectedId ?? ''} onChange={(e) => setSelectedId(Number(e.target.value))}>
            {classes.map((c) => (
              <option key={c.id} value={c.id}>{c.class_code} — {c.subject_name}</option>
            ))}
          </select>
          <button className="btn btn-primary" onClick={exportExcel} disabled={exporting || !rows?.length}>
            <DownloadSimple size={16} weight="bold" /> {exporting ? 'Đang xuất…' : 'Xuất Excel'}
          </button>
        </div>
      </div>

      <div className="table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              <th>MSSV</th>
              <th>Họ tên</th>
              <th>Có mặt</th>
              <th>Muộn</th>
              <th>Vắng</th>
              <th>Tổng buổi</th>
              <th>Trạng thái</th>
            </tr>
          </thead>
          <tbody>
            {rows === null ? (
              <tr>
                <td colSpan={7} style={{ textAlign: 'center', padding: 24 }}>
                  <div className="skeleton" style={{ height: 16, borderRadius: 4 }} />
                </td>
              </tr>
            ) : rows.length ? (
              rows.map((r) => (
                <tr key={r.student_code}>
                  <td>{r.student_code}</td>
                  <td>{r.full_name}</td>
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
              ))
            ) : (
              <tr>
                <td colSpan={7} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 24 }}>
                  Lớp này chưa có buổi điểm danh nào được đóng
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
