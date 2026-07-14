import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { MagnifyingGlass, PencilSimple, Plus, Trash } from '@phosphor-icons/react'
import api from '../api'
import Modal from '../components/Modal'
import Pagination from '../components/Pagination'
import { formatSemester, generateSemesterOptions } from '../utils/format'

const PAGE_SIZE = 10
const emptyForm = { class_code: '', subject_name: '', lecturer_id: '', semester: '' }
const SEMESTER_OPTIONS = generateSemesterOptions()

/** Quan ly lop hoc phan (chi admin): bang trang kieu DAU - tim kiem, phan trang, modal
 * them/sua, xoa co confirm. Click 1 dong -> trang chi tiet (tab Sinh vien / Lich hoc). */
export default function Classes() {
  const navigate = useNavigate()
  const [rows, setRows] = useState(null)
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [query, setQuery] = useState('')
  const [debouncedQuery, setDebouncedQuery] = useState('')
  const [lecturers, setLecturers] = useState([])
  const [modalMode, setModalMode] = useState(null)
  const [editingRow, setEditingRow] = useState(null)
  const [form, setForm] = useState(emptyForm)
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    api.get('/lecturers').then(({ data }) => setLecturers(data))
  }, [])

  useEffect(() => {
    const id = setTimeout(() => {
      setDebouncedQuery(query)
      setPage(1)
    }, 300)
    return () => clearTimeout(id)
  }, [query])

  const load = () => {
    api.get('/classes', {
      params: { q: debouncedQuery || undefined, limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE },
    }).then(({ data, headers }) => {
      setRows(data)
      setTotal(Number(headers['x-total-count'] ?? data.length))
    })
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedQuery, page])

  const openCreate = () => {
    setForm(emptyForm)
    setError('')
    setModalMode('create')
  }

  const openEdit = (c) => {
    setEditingRow(c)
    setForm({ class_code: c.class_code, subject_name: c.subject_name,
             lecturer_id: String(c.lecturer_id), semester: c.semester })
    setError('')
    setModalMode('edit')
  }

  const closeModal = () => {
    setModalMode(null)
    setEditingRow(null)
  }

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      const body = { ...form, lecturer_id: Number(form.lecturer_id) }
      if (modalMode === 'create') {
        await api.post('/classes', body)
      } else {
        await api.patch(`/classes/${editingRow.id}`, body)
      }
      closeModal()
      load()
    } catch (err) {
      setError(err.response?.data?.detail || 'Không lưu được lớp học phần.')
    } finally {
      setSubmitting(false)
    }
  }

  const remove = async (c) => {
    if (!window.confirm(`Xóa lớp học phần ${c.class_code}?`)) return
    try {
      await api.delete(`/classes/${c.id}`)
      load()
    } catch (err) {
      alert(err.response?.data?.detail || 'Không xóa được lớp học phần.')
    }
  }

  const lecturerName = (id) => lecturers.find((l) => l.id === id)?.full_name || `#${id}`

  return (
    <div>
      <div className="admin-toolbar">
        <div className="admin-toolbar-search">
          <MagnifyingGlass size={16} />
          <input
            placeholder="Tìm theo mã lớp hoặc tên môn…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
        <button className="btn btn-brand" onClick={openCreate}>
          <Plus size={16} weight="bold" /> Thêm mới
        </button>
      </div>

      <div className="card">
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
              {rows?.map((c) => (
                <tr key={c.id} className="row-clickable" onClick={() => navigate(`/admin/classes/${c.id}`)}>
                  <td>{c.class_code}</td>
                  <td>{c.subject_name}</td>
                  <td>{lecturerName(c.lecturer_id)}</td>
                  <td>{formatSemester(c.semester)}</td>
                  <td>
                    <div style={{ display: 'flex', gap: 6 }} onClick={(e) => e.stopPropagation()}>
                      <button className="icon-btn" onClick={() => openEdit(c)} aria-label="Sửa">
                        <PencilSimple size={16} />
                      </button>
                      <button className="icon-btn" onClick={() => remove(c)} aria-label="Xóa">
                        <Trash size={16} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {rows && !rows.length && (
                <tr>
                  <td colSpan={5} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 24 }}>
                    {debouncedQuery ? 'Không tìm thấy lớp học phần phù hợp' : 'Chưa có lớp học phần nào'}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <Pagination page={page} pageSize={PAGE_SIZE} total={total} onPageChange={setPage} />
      </div>

      {modalMode && (
        <Modal title={modalMode === 'create' ? 'Thêm lớp học phần mới' : `Sửa lớp học phần — ${editingRow.class_code}`} onClose={closeModal}>
          <form onSubmit={submit} className="modal-form" style={{ marginTop: 16 }}>
            <div className="field">
              <label>Mã lớp</label>
              <input required value={form.class_code} onChange={(e) => setForm({ ...form, class_code: e.target.value })} />
            </div>
            <div className="field">
              <label>Tên môn học</label>
              <input required value={form.subject_name} onChange={(e) => setForm({ ...form, subject_name: e.target.value })} />
            </div>
            <div className="field">
              <label>Giảng viên</label>
              <select
                className="select"
                required
                value={form.lecturer_id}
                onChange={(e) => setForm({ ...form, lecturer_id: e.target.value })}
              >
                <option value="">— Chọn —</option>
                {lecturers.map((l) => (
                  <option key={l.id} value={l.id}>{l.full_name} ({l.lecturer_code})</option>
                ))}
              </select>
            </div>
            <div className="field">
              <label>Học kỳ</label>
              <select
                className="select"
                required
                value={form.semester}
                onChange={(e) => setForm({ ...form, semester: e.target.value })}
              >
                <option value="">— Chọn học kỳ —</option>
                {SEMESTER_OPTIONS.map((s) => (
                  <option key={s} value={s}>{formatSemester(s)}</option>
                ))}
              </select>
            </div>
            <div style={{ gridColumn: '1 / -1', display: 'flex', alignItems: 'center', gap: 12, marginTop: 4 }}>
              <button type="submit" className="btn btn-primary" disabled={submitting}>
                {submitting ? 'Đang lưu…' : 'Lưu'}
              </button>
              {error && <span className="field-error">{error}</span>}
            </div>
          </form>
        </Modal>
      )}
    </div>
  )
}
