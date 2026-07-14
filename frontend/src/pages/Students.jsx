import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { MagnifyingGlass, Plus, Trash, PencilSimple } from '@phosphor-icons/react'
import api from '../api'
import Modal from '../components/Modal'
import Pagination from '../components/Pagination'

const PAGE_SIZE = 10
const emptyForm = { email: '', password: '', full_name: '', student_code: '', major: '', cohort: '' }

/** Quan ly sinh vien (chi admin): bang trang kieu DAU - tim kiem, phan trang, modal them/sua, xoa co confirm. */
export default function Students() {
  const [searchParams] = useSearchParams()
  const [rows, setRows] = useState(null)
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [query, setQuery] = useState(searchParams.get('q') || '')
  const [debouncedQuery, setDebouncedQuery] = useState(query)
  const [modalMode, setModalMode] = useState(null) // null | 'create' | 'edit'
  const [editingRow, setEditingRow] = useState(null)
  const [form, setForm] = useState(emptyForm)
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    const id = setTimeout(() => {
      setDebouncedQuery(query)
      setPage(1)
    }, 300)
    return () => clearTimeout(id)
  }, [query])

  const load = () => {
    api.get('/students', {
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

  const openEdit = (s) => {
    setEditingRow(s)
    setForm({ ...emptyForm, full_name: s.full_name, major: s.major, cohort: String(s.cohort) })
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
      if (modalMode === 'create') {
        await api.post('/students', { ...form, cohort: Number(form.cohort) || 0 })
      } else {
        await api.patch(`/students/${editingRow.id}`, {
          full_name: form.full_name, major: form.major, cohort: Number(form.cohort) || 0,
        })
      }
      closeModal()
      load()
    } catch (err) {
      setError(err.response?.data?.detail || 'Không lưu được sinh viên.')
    } finally {
      setSubmitting(false)
    }
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
      <div className="admin-toolbar">
        <div className="admin-toolbar-search">
          <MagnifyingGlass size={16} />
          <input
            placeholder="Tìm theo MSSV hoặc họ tên…"
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
              {rows?.map((s) => (
                <tr key={s.id}>
                  <td>{s.student_code}</td>
                  <td>{s.full_name}</td>
                  <td>{s.major || '—'}</td>
                  <td>{s.cohort || '—'}</td>
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
                      <button className="icon-btn" onClick={() => openEdit(s)} aria-label="Sửa">
                        <PencilSimple size={16} />
                      </button>
                      <button className="icon-btn" onClick={() => remove(s)} aria-label="Xóa">
                        <Trash size={16} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {rows && !rows.length && (
                <tr>
                  <td colSpan={7} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 24 }}>
                    {debouncedQuery ? 'Không tìm thấy sinh viên phù hợp' : 'Chưa có sinh viên nào'}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <Pagination page={page} pageSize={PAGE_SIZE} total={total} onPageChange={setPage} />
      </div>

      {modalMode && (
        <Modal title={modalMode === 'create' ? 'Thêm sinh viên mới' : `Sửa sinh viên — ${editingRow.student_code}`} onClose={closeModal}>
          <form onSubmit={submit} className="modal-form" style={{ marginTop: 16 }}>
            {modalMode === 'create' && (
              <>
                <div className="field">
                  <label>Email</label>
                  <input required type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
                </div>
                <div className="field">
                  <label>Mật khẩu</label>
                  <input required minLength={6} type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
                </div>
              </>
            )}
            <div className="field">
              <label>Họ tên</label>
              <input required value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} />
            </div>
            {modalMode === 'create' && (
              <div className="field">
                <label>MSSV</label>
                <input required value={form.student_code} onChange={(e) => setForm({ ...form, student_code: e.target.value })} />
              </div>
            )}
            <div className="field">
              <label>Ngành</label>
              <input value={form.major} onChange={(e) => setForm({ ...form, major: e.target.value })} />
            </div>
            <div className="field">
              <label>Khóa</label>
              <input type="number" min="2000" value={form.cohort} onChange={(e) => setForm({ ...form, cohort: e.target.value })} />
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
