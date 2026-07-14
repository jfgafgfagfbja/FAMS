import { useEffect, useState } from 'react'
import { Trash, Plus } from '@phosphor-icons/react'
import api from '../api'

const WEEKDAYS = ['Thứ 2', 'Thứ 3', 'Thứ 4', 'Thứ 5', 'Thứ 6', 'Thứ 7', 'Chủ nhật']

const emptyClassForm = { class_code: '', subject_name: '', lecturer_id: '', semester: '' }
const emptyLecturerForm = { email: '', password: '', full_name: '', lecturer_code: '', department: '' }
const emptyScheduleForm = { weekday: '0', start_time: '07:00', end_time: '09:00', room: '' }

/** Quan ly lop hoc phan (chi admin): tao lop, xoa, quan ly lich hoc + ghi danh sinh vien. */
export default function Classes() {
  const [classes, setClasses] = useState(null)
  const [lecturers, setLecturers] = useState([])
  const [allStudents, setAllStudents] = useState([])
  const [classForm, setClassForm] = useState(emptyClassForm)
  const [showLecturerForm, setShowLecturerForm] = useState(false)
  const [lecturerForm, setLecturerForm] = useState(emptyLecturerForm)
  const [selectedId, setSelectedId] = useState(null)
  const [schedules, setSchedules] = useState([])
  const [enrolled, setEnrolled] = useState([])
  const [scheduleForm, setScheduleForm] = useState(emptyScheduleForm)
  const [enrollStudentId, setEnrollStudentId] = useState('')
  const [error, setError] = useState('')

  const loadClasses = () => api.get('/classes').then(({ data }) => setClasses(data))
  const loadLecturers = () => api.get('/lecturers').then(({ data }) => setLecturers(data))
  const loadStudents = () => api.get('/students').then(({ data }) => setAllStudents(data))

  useEffect(() => {
    loadClasses()
    loadLecturers()
    loadStudents()
  }, [])

  const loadDetail = (classId) => {
    setSelectedId(classId)
    api.get(`/classes/${classId}/schedules`).then(({ data }) => setSchedules(data))
    api.get(`/classes/${classId}/students`).then(({ data }) => setEnrolled(data))
  }

  const createClass = async (e) => {
    e.preventDefault()
    setError('')
    try {
      await api.post('/classes', { ...classForm, lecturer_id: Number(classForm.lecturer_id) })
      setClassForm(emptyClassForm)
      loadClasses()
    } catch (err) {
      setError(err.response?.data?.detail || 'Không tạo được lớp học phần.')
    }
  }

  const deleteClass = async (c) => {
    if (!window.confirm(`Xóa lớp ${c.class_code}?`)) return
    await api.delete(`/classes/${c.id}`)
    if (selectedId === c.id) setSelectedId(null)
    loadClasses()
  }

  const createLecturer = async (e) => {
    e.preventDefault()
    setError('')
    try {
      const { data } = await api.post('/lecturers', lecturerForm)
      setLecturerForm(emptyLecturerForm)
      setShowLecturerForm(false)
      await loadLecturers()
      setClassForm((f) => ({ ...f, lecturer_id: String(data.id) }))
    } catch (err) {
      setError(err.response?.data?.detail || 'Không tạo được giảng viên.')
    }
  }

  const addSchedule = async (e) => {
    e.preventDefault()
    await api.post('/classes/schedules', {
      class_id: selectedId,
      weekday: Number(scheduleForm.weekday),
      start_time: scheduleForm.start_time,
      end_time: scheduleForm.end_time,
      room: scheduleForm.room,
    })
    setScheduleForm(emptyScheduleForm)
    loadDetail(selectedId)
  }

  const removeSchedule = async (scheduleId) => {
    await api.delete(`/classes/schedules/${scheduleId}`)
    loadDetail(selectedId)
  }

  const addEnrollment = async (e) => {
    e.preventDefault()
    if (!enrollStudentId) return
    try {
      await api.post(`/classes/${selectedId}/enroll/${enrollStudentId}`)
      setEnrollStudentId('')
      loadDetail(selectedId)
    } catch (err) {
      alert(err.response?.data?.detail || 'Không ghi danh được.')
    }
  }

  const removeEnrollment = async (studentId) => {
    await api.delete(`/classes/${selectedId}/enroll/${studentId}`)
    loadDetail(selectedId)
  }

  const selectedClass = classes?.find((c) => c.id === selectedId)
  const enrollableStudents = allStudents.filter((s) => !enrolled.some((e) => e.id === s.id))

  return (
    <div>
      <div className="card" style={{ padding: 20, marginBottom: 20 }}>
        <h3 style={{ marginTop: 0, fontSize: 15 }}>Thêm lớp học phần</h3>
        <form onSubmit={createClass} style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, alignItems: 'end' }}>
          <div className="field">
            <label>Mã lớp</label>
            <input required value={classForm.class_code} onChange={(e) => setClassForm({ ...classForm, class_code: e.target.value })} />
          </div>
          <div className="field">
            <label>Tên môn học</label>
            <input required value={classForm.subject_name} onChange={(e) => setClassForm({ ...classForm, subject_name: e.target.value })} />
          </div>
          <div className="field">
            <label>Giảng viên</label>
            <select
              className="select"
              required
              value={classForm.lecturer_id}
              onChange={(e) => setClassForm({ ...classForm, lecturer_id: e.target.value })}
            >
              <option value="">— Chọn —</option>
              {lecturers.map((l) => (
                <option key={l.id} value={l.id}>
                  {l.full_name} ({l.lecturer_code})
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>Học kỳ</label>
            <input required placeholder="vd: 2026.1" value={classForm.semester} onChange={(e) => setClassForm({ ...classForm, semester: e.target.value })} />
          </div>
          <div style={{ gridColumn: '1 / -1', display: 'flex', alignItems: 'center', gap: 12 }}>
            <button type="submit" className="btn btn-primary">Tạo lớp</button>
            <button type="button" className="btn btn-ghost" onClick={() => setShowLecturerForm((v) => !v)}>
              <Plus size={16} /> Giảng viên mới
            </button>
            {error && <span className="field-error">{error}</span>}
          </div>
        </form>

        {showLecturerForm && (
          <form onSubmit={createLecturer} className="card" style={{ padding: 16, marginTop: 16, background: 'var(--surface-hover)', border: 'none', display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
            <div className="field">
              <label>Email</label>
              <input required type="email" value={lecturerForm.email} onChange={(e) => setLecturerForm({ ...lecturerForm, email: e.target.value })} />
            </div>
            <div className="field">
              <label>Mật khẩu</label>
              <input required type="password" value={lecturerForm.password} onChange={(e) => setLecturerForm({ ...lecturerForm, password: e.target.value })} />
            </div>
            <div className="field">
              <label>Họ tên</label>
              <input required value={lecturerForm.full_name} onChange={(e) => setLecturerForm({ ...lecturerForm, full_name: e.target.value })} />
            </div>
            <div className="field">
              <label>Mã giảng viên</label>
              <input required value={lecturerForm.lecturer_code} onChange={(e) => setLecturerForm({ ...lecturerForm, lecturer_code: e.target.value })} />
            </div>
            <div className="field">
              <label>Khoa/Bộ môn</label>
              <input value={lecturerForm.department} onChange={(e) => setLecturerForm({ ...lecturerForm, department: e.target.value })} />
            </div>
            <div style={{ display: 'flex', alignItems: 'end' }}>
              <button type="submit" className="btn btn-primary">Tạo giảng viên</button>
            </div>
          </form>
        )}
      </div>

      <div className="card" style={{ marginBottom: 20 }}>
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Mã lớp</th>
                <th>Môn học</th>
                <th>Giảng viên</th>
                <th>Học kỳ</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {classes?.map((c) => (
                <tr
                  key={c.id}
                  onClick={() => loadDetail(c.id)}
                  style={{ cursor: 'pointer', background: selectedId === c.id ? 'var(--accent-soft)' : undefined }}
                >
                  <td>{c.class_code}</td>
                  <td>{c.subject_name}</td>
                  <td>{lecturers.find((l) => l.id === c.lecturer_id)?.full_name || `#${c.lecturer_id}`}</td>
                  <td>{c.semester}</td>
                  <td>
                    <button className="icon-btn" onClick={(e) => { e.stopPropagation(); deleteClass(c) }} aria-label="Xóa">
                      <Trash size={16} />
                    </button>
                  </td>
                </tr>
              ))}
              {classes && !classes.length && (
                <tr>
                  <td colSpan={5} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 24 }}>
                    Chưa có lớp học phần nào
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {selectedClass && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
          <div className="card" style={{ padding: 16 }}>
            <h3 style={{ margin: '0 0 12px', fontSize: 14 }}>Lịch học — {selectedClass.class_code}</h3>
            <div style={{ display: 'grid', gap: 8, marginBottom: 12 }}>
              {schedules.map((s) => (
                <div key={s.id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 13.5 }}>
                  <span>{WEEKDAYS[s.weekday]} · {s.start_time}–{s.end_time} · Phòng {s.room}</span>
                  <button className="icon-btn" onClick={() => removeSchedule(s.id)} aria-label="Xóa lịch">
                    <Trash size={14} />
                  </button>
                </div>
              ))}
              {!schedules.length && <p style={{ color: 'var(--text-muted)', fontSize: 13, margin: 0 }}>Chưa có lịch học.</p>}
            </div>
            <form onSubmit={addSchedule} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: 8 }}>
              <select className="select" value={scheduleForm.weekday} onChange={(e) => setScheduleForm({ ...scheduleForm, weekday: e.target.value })}>
                {WEEKDAYS.map((w, i) => <option key={i} value={i}>{w}</option>)}
              </select>
              <input type="time" value={scheduleForm.start_time} onChange={(e) => setScheduleForm({ ...scheduleForm, start_time: e.target.value })} />
              <input type="time" value={scheduleForm.end_time} onChange={(e) => setScheduleForm({ ...scheduleForm, end_time: e.target.value })} />
              <input placeholder="Phòng" required value={scheduleForm.room} onChange={(e) => setScheduleForm({ ...scheduleForm, room: e.target.value })} />
              <button type="submit" className="btn btn-primary" style={{ gridColumn: '1 / -1' }}>Thêm lịch học</button>
            </form>
          </div>

          <div className="card" style={{ padding: 16 }}>
            <h3 style={{ margin: '0 0 12px', fontSize: 14 }}>Sinh viên ghi danh — {selectedClass.class_code}</h3>
            <div style={{ display: 'grid', gap: 8, marginBottom: 12 }}>
              {enrolled.map((s) => (
                <div key={s.id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 13.5 }}>
                  <span>{s.student_code} — {s.full_name}</span>
                  <button className="icon-btn" onClick={() => removeEnrollment(s.id)} aria-label="Hủy ghi danh">
                    <Trash size={14} />
                  </button>
                </div>
              ))}
              {!enrolled.length && <p style={{ color: 'var(--text-muted)', fontSize: 13, margin: 0 }}>Chưa có sinh viên nào.</p>}
            </div>
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
        </div>
      )}
    </div>
  )
}
