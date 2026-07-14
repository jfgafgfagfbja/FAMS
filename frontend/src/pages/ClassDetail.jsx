import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { CaretLeft, Trash, PencilSimple, Plus, UploadSimple, CheckCircle, XCircle } from '@phosphor-icons/react'
import api from '../api'
import Modal from '../components/Modal'
import { WEEKDAYS, formatSemester } from '../utils/format'

const TABS = [
  { key: 'students', label: 'Sinh viên' },
  { key: 'schedule', label: 'Lịch học' },
]

const emptyScheduleForm = { weekday: '0', start_time: '07:00', end_time: '09:00', room: '' }

function parseCsvCodes(text) {
  const lines = text.split(/\r?\n/).map((l) => l.trim()).filter(Boolean)
  if (!lines.length) return []
  const looksLikeHeader = /mssv|student_code/i.test(lines[0])
  const dataLines = looksLikeHeader ? lines.slice(1) : lines
  return dataLines.map((line) => line.split(',')[0].trim()).filter(Boolean)
}

/** Chi tiet 1 lop hoc phan (admin): tab Sinh vien (ghi danh/huy ghi danh + import CSV)
 * va tab Lich hoc (CRUD lich hoc cua rieng lop nay). */
export default function ClassDetail() {
  const { classId } = useParams()
  const [tab, setTab] = useState('students')
  const [clazz, setClazz] = useState(null)
  const [lecturer, setLecturer] = useState(null)

  const [enrolled, setEnrolled] = useState(null)
  const [allStudents, setAllStudents] = useState([])
  const [enrollStudentId, setEnrollStudentId] = useState('')
  const [csvRows, setCsvRows] = useState(null)
  const [importing, setImporting] = useState(false)

  const [schedules, setSchedules] = useState(null)
  const [scheduleModal, setScheduleModal] = useState(null) // null | 'create' | 'edit'
  const [editingSchedule, setEditingSchedule] = useState(null)
  const [scheduleForm, setScheduleForm] = useState(emptyScheduleForm)
  const [scheduleError, setScheduleError] = useState('')
  const [savingSchedule, setSavingSchedule] = useState(false)

  const loadClass = () => api.get(`/classes/${classId}`).then(({ data }) => {
    setClazz(data)
    api.get('/lecturers').then(({ data: lecturers }) => {
      setLecturer(lecturers.find((l) => l.id === data.lecturer_id) || null)
    })
  })
  const loadEnrolled = () => api.get(`/classes/${classId}/students`).then(({ data }) => setEnrolled(data))
  const loadAllStudents = () => api.get('/students').then(({ data }) => setAllStudents(data))
  const loadSchedules = () => api.get(`/classes/${classId}/schedules`).then(({ data }) => setSchedules(data))

  useEffect(() => {
    loadClass()
    loadEnrolled()
    loadAllStudents()
    loadSchedules()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [classId])

  const addEnrollment = async (e) => {
    e.preventDefault()
    if (!enrollStudentId) return
    try {
      await api.post(`/classes/${classId}/enroll/${enrollStudentId}`)
      setEnrollStudentId('')
      loadEnrolled()
    } catch (err) {
      alert(err.response?.data?.detail || 'Không ghi danh được.')
    }
  }

  const removeEnrollment = async (studentId) => {
    await api.delete(`/classes/${classId}/enroll/${studentId}`)
    loadEnrolled()
  }

  const handleCsvFile = (e) => {
    const file = e.target.files[0]
    e.target.value = ''
    if (!file) return
    const reader = new FileReader()
    reader.onload = () => {
      const codes = parseCsvCodes(String(reader.result))
      const rows = codes.map((code) => {
        const student = allStudents.find((s) => s.student_code.toLowerCase() === code.toLowerCase())
        const alreadyEnrolled = enrolled?.some((s) => s.student_code.toLowerCase() === code.toLowerCase())
        if (!student) return { code, status: 'error', message: 'Không tìm thấy MSSV trong hệ thống' }
        if (alreadyEnrolled) return { code, studentId: student.id, status: 'error', message: 'Đã ghi danh lớp này' }
        return { code, studentId: student.id, status: 'pending', message: '' }
      })
      setCsvRows(rows)
    }
    reader.readAsText(file)
  }

  const runCsvImport = async () => {
    setImporting(true)
    for (let i = 0; i < csvRows.length; i++) {
      if (csvRows[i].status !== 'pending') continue
      try {
        await api.post(`/classes/${classId}/enroll/${csvRows[i].studentId}`)
        setCsvRows((rows) => rows.map((r, idx) => (idx === i ? { ...r, status: 'success' } : r)))
      } catch (err) {
        setCsvRows((rows) => rows.map((r, idx) => (
          idx === i ? { ...r, status: 'error', message: err.response?.data?.detail || 'Lỗi không xác định' } : r
        )))
      }
    }
    setImporting(false)
    loadEnrolled()
  }

  const enrollableStudents = allStudents.filter((s) => !enrolled?.some((e) => e.id === s.id))

  const openCreateSchedule = () => {
    setScheduleForm(emptyScheduleForm)
    setScheduleError('')
    setScheduleModal('create')
  }

  const openEditSchedule = (s) => {
    setEditingSchedule(s)
    setScheduleForm({ weekday: String(s.weekday), start_time: s.start_time.slice(0, 5),
                     end_time: s.end_time.slice(0, 5), room: s.room })
    setScheduleError('')
    setScheduleModal('edit')
  }

  const closeScheduleModal = () => {
    setScheduleModal(null)
    setEditingSchedule(null)
  }

  const submitSchedule = async (e) => {
    e.preventDefault()
    setScheduleError('')
    if (scheduleForm.end_time <= scheduleForm.start_time) {
      setScheduleError('Giờ kết thúc phải sau giờ bắt đầu.')
      return
    }
    setSavingSchedule(true)
    try {
      const body = { weekday: Number(scheduleForm.weekday), start_time: scheduleForm.start_time,
                    end_time: scheduleForm.end_time, room: scheduleForm.room }
      if (scheduleModal === 'create') {
        await api.post('/classes/schedules', { ...body, class_id: Number(classId) })
      } else {
        await api.patch(`/classes/schedules/${editingSchedule.id}`, body)
      }
      closeScheduleModal()
      loadSchedules()
    } catch (err) {
      setScheduleError(err.response?.data?.detail || 'Không lưu được lịch học.')
    } finally {
      setSavingSchedule(false)
    }
  }

  const removeSchedule = async (s) => {
    if (!window.confirm(`Xóa lịch học ${WEEKDAYS[s.weekday]} ${s.start_time.slice(0, 5)}–${s.end_time.slice(0, 5)}?`)) return
    try {
      await api.delete(`/classes/schedules/${s.id}`)
      loadSchedules()
    } catch (err) {
      alert(err.response?.data?.detail || 'Không xóa được lịch học.')
    }
  }

  if (!clazz) {
    return <div className="card skeleton" style={{ height: 300 }} />
  }

  return (
    <div>
      <Link to="/admin/classes" style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: 13, color: 'var(--text-muted)', textDecoration: 'none', marginBottom: 12 }}>
        <CaretLeft size={14} /> Lớp học phần
      </Link>

      <div className="card" style={{ padding: 20, marginBottom: 20 }}>
        <h2 style={{ margin: 0 }}>{clazz.class_code} — {clazz.subject_name}</h2>
        <p style={{ margin: '4px 0 0', color: 'var(--text-muted)', fontSize: 13.5 }}>
          GV: {lecturer?.full_name || `#${clazz.lecturer_id}`} · {formatSemester(clazz.semester)}
        </p>
      </div>

      <div className="tab-bar">
        {TABS.map((t) => (
          <button
            key={t.key}
            className={`tab-btn${tab === t.key ? ' active' : ''}`}
            onClick={() => setTab(t.key)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'students' && (
        <div>
          <div className="card" style={{ padding: 16, marginBottom: 20 }}>
            <h3 style={{ marginTop: 0, fontSize: 14 }}>Nhập danh sách từ CSV</h3>
            <p style={{ fontSize: 12.5, color: 'var(--text-muted)', marginTop: 0 }}>
              File CSV có 1 MSSV mỗi dòng (cột đầu tiên). Có thể có dòng tiêu đề "mssv"/"student_code".
            </p>
            <label className="btn btn-ghost" style={{ display: 'inline-flex', cursor: 'pointer' }}>
              <UploadSimple size={16} /> Chọn file CSV
              <input type="file" accept=".csv,text/csv" onChange={handleCsvFile} style={{ display: 'none' }} />
            </label>

            {csvRows && (
              <div style={{ marginTop: 16 }}>
                <div className="card" style={{ background: 'var(--surface-hover)', border: 'none' }}>
                  {csvRows.map((r, i) => (
                    <div key={i} className="csv-preview-row">
                      <span>{r.code}</span>
                      {r.status === 'pending' && <span className="tag tag-neutral">Chờ nhập</span>}
                      {r.status === 'success' && (
                        <span className="tag tag-success"><CheckCircle size={12} weight="fill" style={{ verticalAlign: -1 }} /> Thành công</span>
                      )}
                      {r.status === 'error' && (
                        <span className="tag tag-danger" title={r.message}>
                          <XCircle size={12} weight="fill" style={{ verticalAlign: -1 }} /> {r.message}
                        </span>
                      )}
                    </div>
                  ))}
                </div>
                <div style={{ display: 'flex', gap: 10, marginTop: 12 }}>
                  <button
                    className="btn btn-primary"
                    onClick={runCsvImport}
                    disabled={importing || !csvRows.some((r) => r.status === 'pending')}
                  >
                    {importing ? 'Đang nhập…' : 'Bắt đầu nhập'}
                  </button>
                  <button className="btn btn-ghost" onClick={() => setCsvRows(null)} disabled={importing}>Đóng</button>
                </div>
              </div>
            )}
          </div>

          <div className="card" style={{ padding: 16, marginBottom: 20 }}>
            <h3 style={{ marginTop: 0, fontSize: 14 }}>Ghi danh sinh viên</h3>
            <form onSubmit={addEnrollment} style={{ display: 'flex', gap: 8 }}>
              <select className="select" style={{ flex: 1 }} value={enrollStudentId} onChange={(e) => setEnrollStudentId(e.target.value)}>
                <option value="">— Chọn sinh viên —</option>
                {enrollableStudents.map((s) => (
                  <option key={s.id} value={s.id}>{s.student_code} — {s.full_name}</option>
                ))}
              </select>
              <button type="submit" className="btn btn-primary" disabled={!enrollStudentId}>Ghi danh</button>
            </form>
          </div>

          <div className="card">
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>MSSV</th>
                    <th>Họ tên</th>
                    <th>Ngành</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {enrolled?.map((s) => (
                    <tr key={s.id}>
                      <td>{s.student_code}</td>
                      <td>{s.full_name}</td>
                      <td>{s.major || '—'}</td>
                      <td>
                        <button className="icon-btn" onClick={() => removeEnrollment(s.id)} aria-label="Hủy ghi danh">
                          <Trash size={16} />
                        </button>
                      </td>
                    </tr>
                  ))}
                  {enrolled && !enrolled.length && (
                    <tr>
                      <td colSpan={4} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 24 }}>
                        Chưa có sinh viên nào ghi danh
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {tab === 'schedule' && (
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'flex-end', padding: 16, paddingBottom: 0 }}>
            <button className="btn btn-brand" onClick={openCreateSchedule}>
              <Plus size={16} weight="bold" /> Thêm lịch học
            </button>
          </div>
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Thứ</th>
                  <th>Giờ</th>
                  <th>Phòng</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {schedules?.map((s) => (
                  <tr key={s.id}>
                    <td>{WEEKDAYS[s.weekday]}</td>
                    <td>{s.start_time.slice(0, 5)}–{s.end_time.slice(0, 5)}</td>
                    <td>{s.room}</td>
                    <td>
                      <div style={{ display: 'flex', gap: 6 }}>
                        <button className="icon-btn" onClick={() => openEditSchedule(s)} aria-label="Sửa">
                          <PencilSimple size={16} />
                        </button>
                        <button className="icon-btn" onClick={() => removeSchedule(s)} aria-label="Xóa">
                          <Trash size={16} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
                {schedules && !schedules.length && (
                  <tr>
                    <td colSpan={4} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 24 }}>
                      Chưa có lịch học nào
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {scheduleModal && (
        <Modal title={scheduleModal === 'create' ? 'Thêm lịch học' : 'Sửa lịch học'} onClose={closeScheduleModal} width={420}>
          <form onSubmit={submitSchedule} className="modal-form" style={{ marginTop: 16 }}>
            <div className="field">
              <label>Thứ</label>
              <select className="select" value={scheduleForm.weekday} onChange={(e) => setScheduleForm({ ...scheduleForm, weekday: e.target.value })}>
                {WEEKDAYS.map((w, i) => <option key={i} value={i}>{w}</option>)}
              </select>
            </div>
            <div className="field">
              <label>Phòng</label>
              <input required value={scheduleForm.room} onChange={(e) => setScheduleForm({ ...scheduleForm, room: e.target.value })} />
            </div>
            <div className="field">
              <label>Giờ bắt đầu</label>
              <input type="time" required value={scheduleForm.start_time} onChange={(e) => setScheduleForm({ ...scheduleForm, start_time: e.target.value })} />
            </div>
            <div className="field">
              <label>Giờ kết thúc</label>
              <input type="time" required value={scheduleForm.end_time} onChange={(e) => setScheduleForm({ ...scheduleForm, end_time: e.target.value })} />
            </div>
            <div style={{ gridColumn: '1 / -1', display: 'flex', alignItems: 'center', gap: 12, marginTop: 4 }}>
              <button type="submit" className="btn btn-primary" disabled={savingSchedule}>
                {savingSchedule ? 'Đang lưu…' : 'Lưu'}
              </button>
              {scheduleError && <span className="field-error">{scheduleError}</span>}
            </div>
          </form>
        </Modal>
      )}
    </div>
  )
}
