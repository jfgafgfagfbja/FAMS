import { useEffect, useState } from 'react'
import { Trash, PencilSimple, Check, X } from '@phosphor-icons/react'
import api from '../api'

const emptyForm = { email: '', password: '', full_name: '', student_code: '', major: '', cohort: '' }

/** Quan ly sinh vien (chi admin): tao moi, sua thong tin, xoa. */
export default function Students() {
  const [students, setStudents] = useState(null)
  const [form, setForm] = useState(emptyForm)
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [editingId, setEditingId] = useState(null)
  const [editForm, setEditForm] = useState({ full_name: '', major: '', cohort: '' })

  const load = () => api.get('/students').then(({ data }) => setStudents(data))

  useEffect(() => {
    load()
  }, [])

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      await api.post('/students', {
        ...form,
        cohort: Number(form.cohort) || 0,
      })
      setForm(emptyForm)
      load()
    } catch (err) {
      setError(err.response?.data?.detail || 'Không tạo được sinh viên.')
    } finally {
      setSubmitting(false)
    }
  }

  const startEdit = (s) => {
    setEditingId(s.id)
    setEditForm({ full_name: s.full_name, major: s.major, cohort: s.cohort })
  }

  const saveEdit = async (id) => {
    await api.patch(`/students/${id}`, { ...editForm, cohort: Number(editForm.cohort) || 0 })
    setEditingId(null)
    load()
  }

  const remove = async (s) => {
    if (!window.confirm(`Xóa sinh viên ${s.full_name} (${s.student_code})?`)) return
    try {
      await api.delete(`/students/${s.id}`)
      load()
    } catch (err) {
      alert(err.response?.data?.detail || 'Không xóa được sinh viên.')
    }
  }

  return (
    <div>
      <div className="card" style={{ padding: 20, marginBottom: 20 }}>
        <h3 style={{ marginTop: 0, fontSize: 15 }}>Thêm sinh viên mới</h3>
        <form onSubmit={submit} style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
          <div className="field">
            <label>Email</label>
            <input required type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
          </div>
          <div className="field">
            <label>Mật khẩu</label>
            <input required type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
          </div>
          <div className="field">
            <label>Họ tên</label>
            <input required value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} />
          </div>
          <div className="field">
            <label>MSSV</label>
            <input required value={form.student_code} onChange={(e) => setForm({ ...form, student_code: e.target.value })} />
          </div>
          <div className="field">
            <label>Ngành</label>
            <input value={form.major} onChange={(e) => setForm({ ...form, major: e.target.value })} />
          </div>
          <div className="field">
            <label>Khóa</label>
            <input type="number" value={form.cohort} onChange={(e) => setForm({ ...form, cohort: e.target.value })} />
          </div>
          <div style={{ gridColumn: '1 / -1', display: 'flex', alignItems: 'center', gap: 12 }}>
            <button type="submit" className="btn btn-primary" disabled={submitting}>
              {submitting ? 'Đang tạo…' : 'Tạo sinh viên'}
            </button>
            {error && <span className="field-error">{error}</span>}
          </div>
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
                <th>Khóa</th>
                <th>Khuôn mặt</th>
                <th>Đồng ý</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {students?.map((s) => (
                <tr key={s.id}>
                  <td>{s.student_code}</td>
                  <td>
                    {editingId === s.id ? (
                      <input
                        value={editForm.full_name}
                        onChange={(e) => setEditForm({ ...editForm, full_name: e.target.value })}
                        style={{ width: '100%' }}
                      />
                    ) : (
                      s.full_name
                    )}
                  </td>
                  <td>
                    {editingId === s.id ? (
                      <input
                        value={editForm.major}
                        onChange={(e) => setEditForm({ ...editForm, major: e.target.value })}
                        style={{ width: '100%' }}
                      />
                    ) : (
                      s.major
                    )}
                  </td>
                  <td>
                    {editingId === s.id ? (
                      <input
                        type="number"
                        value={editForm.cohort}
                        onChange={(e) => setEditForm({ ...editForm, cohort: e.target.value })}
                        style={{ width: 80 }}
                      />
                    ) : (
                      s.cohort
                    )}
                  </td>
                  <td>
                    {s.face_enrolled ? (
                      <span className="tag tag-success">Đã đăng ký</span>
                    ) : (
                      <span className="tag tag-neutral">Chưa</span>
                    )}
                  </td>
                  <td>
                    {s.consent_given ? (
                      <span className="tag tag-success">Có</span>
                    ) : (
                      <span className="tag tag-neutral">Chưa</span>
                    )}
                  </td>
                  <td>
                    <div style={{ display: 'flex', gap: 6 }}>
                      {editingId === s.id ? (
                        <>
                          <button className="icon-btn" onClick={() => saveEdit(s.id)} aria-label="Lưu">
                            <Check size={16} />
                          </button>
                          <button className="icon-btn" onClick={() => setEditingId(null)} aria-label="Hủy">
                            <X size={16} />
                          </button>
                        </>
                      ) : (
                        <>
                          <button className="icon-btn" onClick={() => startEdit(s)} aria-label="Sửa">
                            <PencilSimple size={16} />
                          </button>
                          <button className="icon-btn" onClick={() => remove(s)} aria-label="Xóa">
                            <Trash size={16} />
                          </button>
                        </>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
              {students && !students.length && (
                <tr>
                  <td colSpan={7} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 24 }}>
                    Chưa có sinh viên nào
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
