import { useEffect, useState } from 'react'
import { MagnifyingGlass, Plus, Trash, PencilSimple } from '@phosphor-icons/react'
import api from '../api'
import Modal from '../components/Modal'
import Pagination from '../components/Pagination'

const PAGE_SIZE = 10
const emptyForm = { email: '', password: '', full_name: '', lecturer_code: '', department: '' }

/** Quan ly giang vien (chi admin): bang trang kieu DAU - tim kiem, phan trang, modal them/sua, xoa co confirm. */
export default function Lecturers() {
  const [rows, setRows] = useState(null)
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [query, setQuery] = useState('')
  const [debouncedQuery, setDebouncedQuery] = useState('')
  const [modalMode, setModalMode] = useState(null)
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
    api.get('/lecturers', {
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

  const openEdit = (l) => {
    setEditingRow(l)
    setForm({ ...emptyForm, full_name: l.full_name, department: l.department })
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
        await api.post('/lecturers', form)
      } else {
        await api.patch(`/lecturers/${editingRow.id}`, {
          full_name: form.full_name, department: form.department,
        })
      }
      closeModal()
      load()
    } catch (err) {
      setError(err.response?.data?.detail || 'Không lưu được giảng viên.')
    } finally {
      setSubmitting(false)
    }
  }

  const remove = async (l) => {
    if (!window.confirm(`Xóa giảng viên ${l.full_name} (${l.lecturer_code})?`)) return
    try {
      await api.delete(`/lecturers/${l.id}`)
      load()
    } catch (err) {
      alert(err.response?.data?.detail || 'Không xóa được giảng viên.')
    }
  }

  return (
    <div>
      <div className="admin-toolbar">
        <div className="admin-toolbar-search">
          <MagnifyingGlass size={16} />
          <input
            placeholder="Tìm theo mã GV hoặc họ tên…"
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
                <th>Mã GV</th>
                <th>Họ tên</th>
                <th>Khoa/Bộ môn</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {rows?.map((l) => (
                <tr key={l.id}>
                  <td>{l.lecturer_code}</td>
                  <td>{l.full_name}</td>
                  <td>{l.department || '—'}</td>
                  <td>
                    <div style={{ display: 'flex', gap: 6 }}>
                      <button className="icon-btn" onClick={() => openEdit(l)} aria-label="Sửa">
                        <PencilSimple size={16} />
                      </button>
                      <button className="icon-btn" onClick={() => remove(l)} aria-label="Xóa">
                        <Trash size={16} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {rows && !rows.length && (
                <tr>
                  <td colSpan={4} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 24 }}>
                    {debouncedQuery ? 'Không tìm thấy giảng viên phù hợp' : 'Chưa có giảng viên nào'}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <Pagination page={page} pageSize={PAGE_SIZE} total={total} onPageChange={setPage} />
      </div>

      {modalMode && (
        <Modal title={modalMode === 'create' ? 'Thêm giảng viên mới' : `Sửa giảng viên — ${editingRow.lecturer_code}`} onClose={closeModal}>
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
                <label>Mã giảng viên</label>
                <input required value={form.lecturer_code} onChange={(e) => setForm({ ...form, lecturer_code: e.target.value })} />
              </div>
            )}
            <div className="field">
              <label>Khoa/Bộ môn</label>
              <input value={form.department} onChange={(e) => setForm({ ...form, department: e.target.value })} />
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
