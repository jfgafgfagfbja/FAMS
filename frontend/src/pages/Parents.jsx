import { useEffect, useState } from 'react'
import { MagnifyingGlass, Plus, Trash, PencilSimple, UsersThree } from '@phosphor-icons/react'
import api from '../api'
import Modal from '../components/Modal'
import Pagination from '../components/Pagination'

const PAGE_SIZE = 10
const emptyForm = { email: '', password: '', full_name: '', phone: '' }

/** Quan ly tai khoan phu huynh (chi admin): bang trang kieu DAU giong
 * Students.jsx/Lecturers.jsx, them modal rieng "Quan ly con em" de lien ket/go
 * lien ket voi sinh vien bang MSSV (admin tao & lien ket thu cong, khong tu dang ky). */
export default function Parents() {
  const [rows, setRows] = useState(null)
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [query, setQuery] = useState('')
  const [debouncedQuery, setDebouncedQuery] = useState('')
  const [modalMode, setModalMode] = useState(null) // null | 'create' | 'edit'
  const [editingRow, setEditingRow] = useState(null)
  const [form, setForm] = useState(emptyForm)
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const [childrenModalRow, setChildrenModalRow] = useState(null)
  const [children, setChildren] = useState(null)
  const [newCode, setNewCode] = useState('')
  const [childError, setChildError] = useState('')
  const [linking, setLinking] = useState(false)

  useEffect(() => {
    const id = setTimeout(() => {
      setDebouncedQuery(query)
      setPage(1)
    }, 300)
    return () => clearTimeout(id)
  }, [query])

  const load = () => {
    api.get('/parents', {
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

  const openEdit = (p) => {
    setEditingRow(p)
    setForm({ ...emptyForm, full_name: p.full_name, phone: p.phone })
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
        await api.post('/parents', form)
      } else {
        await api.patch(`/parents/${editingRow.id}`, { full_name: form.full_name, phone: form.phone })
      }
      closeModal()
      load()
    } catch (err) {
      setError(err.response?.data?.detail || 'Không lưu được phụ huynh.')
    } finally {
      setSubmitting(false)
    }
  }

  const remove = async (p) => {
    if (!window.confirm(`Xóa tài khoản phụ huynh ${p.full_name} (${p.email})?`)) return
    try {
      await api.delete(`/parents/${p.id}`)
      load()
    } catch (err) {
      alert(err.response?.data?.detail || 'Không xóa được phụ huynh.')
    }
  }

  const openChildren = async (p) => {
    setChildrenModalRow(p)
    setChildren(null)
    setNewCode('')
    setChildError('')
    const { data } = await api.get(`/parents/${p.id}/children`)
    setChildren(data)
  }

  const closeChildren = () => {
    setChildrenModalRow(null)
    setChildren(null)
  }

  const linkChild = async (e) => {
    e.preventDefault()
    if (!newCode.trim()) return
    setChildError('')
    setLinking(true)
    try {
      await api.post(`/parents/${childrenModalRow.id}/children`, { student_code: newCode.trim() })
      setNewCode('')
      const { data } = await api.get(`/parents/${childrenModalRow.id}/children`)
      setChildren(data)
      load()
    } catch (err) {
      setChildError(err.response?.data?.detail || 'Không liên kết được sinh viên này.')
    } finally {
      setLinking(false)
    }
  }

  const unlinkChild = async (studentId) => {
    await api.delete(`/parents/${childrenModalRow.id}/children/${studentId}`)
    const { data } = await api.get(`/parents/${childrenModalRow.id}/children`)
    setChildren(data)
    load()
  }

  return (
    <div>
      <div className="admin-toolbar">
        <div className="admin-toolbar-search">
          <MagnifyingGlass size={16} />
          <input
            placeholder="Tìm theo họ tên hoặc email…"
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
                <th>Họ tên</th>
                <th>Email</th>
                <th>SĐT</th>
                <th>Con em</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {rows?.map((p) => (
                <tr key={p.id}>
                  <td>{p.full_name}</td>
                  <td>{p.email}</td>
                  <td>{p.phone || '—'}</td>
                  <td>
                    <button className="btn btn-ghost" style={{ padding: '5px 10px', fontSize: 12 }} onClick={() => openChildren(p)}>
                      <UsersThree size={14} /> {p.child_count} con
                    </button>
                  </td>
                  <td>
                    <div style={{ display: 'flex', gap: 6 }}>
                      <button className="icon-btn" onClick={() => openEdit(p)} aria-label="Sửa">
                        <PencilSimple size={16} />
                      </button>
                      <button className="icon-btn" onClick={() => remove(p)} aria-label="Xóa">
                        <Trash size={16} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {rows && !rows.length && (
                <tr>
                  <td colSpan={5} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 24 }}>
                    {debouncedQuery ? 'Không tìm thấy phụ huynh phù hợp' : 'Chưa có phụ huynh nào'}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <Pagination page={page} pageSize={PAGE_SIZE} total={total} onPageChange={setPage} />
      </div>

      {modalMode && (
        <Modal title={modalMode === 'create' ? 'Thêm phụ huynh mới' : `Sửa phụ huynh — ${editingRow.full_name}`} onClose={closeModal}>
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
            <div className="field">
              <label>Số điện thoại</label>
              <input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
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

      {childrenModalRow && (
        <Modal title={`Con em của ${childrenModalRow.full_name}`} onClose={closeChildren}>
          <div style={{ marginTop: 16 }}>
            {children === null ? (
              <div className="skeleton" style={{ height: 60, borderRadius: 8 }} />
            ) : children.length ? (
              <div style={{ marginBottom: 16 }}>
                {children.map((c) => (
                  <div key={c.id} className="class-list-row">
                    <div>
                      <div className="class-list-code">{c.full_name}</div>
                      <div className="class-list-subject">MSSV {c.student_code}</div>
                    </div>
                    <button className="icon-btn" onClick={() => unlinkChild(c.id)} aria-label="Gỡ liên kết">
                      <Trash size={16} />
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>Chưa liên kết với sinh viên nào.</p>
            )}

            <form onSubmit={linkChild} style={{ display: 'flex', gap: 8 }}>
              <input
                placeholder="Nhập MSSV để liên kết…"
                value={newCode}
                onChange={(e) => setNewCode(e.target.value)}
                style={{ flex: 1 }}
              />
              <button type="submit" className="btn btn-primary" disabled={linking || !newCode.trim()}>
                {linking ? 'Đang liên kết…' : 'Liên kết'}
              </button>
            </form>
            {childError && <p className="field-error" style={{ marginTop: 8 }}>{childError}</p>}
          </div>
        </Modal>
      )}
    </div>
  )
}
