import { useEffect, useState } from 'react'
import { MagnifyingGlass, PencilSimple, Plus, Trash } from '@phosphor-icons/react'
import api from '../api'
import Modal from '../components/Modal'
import Pagination from '../components/Pagination'
import { WEEKDAYS } from '../utils/format'

const PAGE_SIZE = 10
const emptyForm = { class_id: '', weekday: '0', start_time: '07:00', end_time: '09:00', room: '' }

/** Quan ly toan bo lich hoc cua truong (chi admin): bang trang kieu DAU - tim kiem,
 * phan trang, modal them/sua, xoa co confirm. */
export default function AdminSchedules() {
  const [rows, setRows] = useState(null)
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [query, setQuery] = useState('')
  const [debouncedQuery, setDebouncedQuery] = useState('')
  const [classes, setClasses] = useState([])
  const [modalMode, setModalMode] = useState(null)
  const [editingRow, setEditingRow] = useState(null)
  const [form, setForm] = useState(emptyForm)
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    api.get('/classes').then(({ data }) => setClasses(data))
  }, [])

  useEffect(() => {
    const id = setTimeout(() => {
      setDebouncedQuery(query)
      setPage(1)
    }, 300)
    return () => clearTimeout(id)
  }, [query])

  const load = () => {
    api.get('/schedules', {
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
    setForm({ class_id: String(s.class_id), weekday: String(s.weekday),
             start_time: s.start_time.slice(0, 5), end_time: s.end_time.slice(0, 5), room: s.room })
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
    if (form.end_time <= form.start_time) {
      setError('Giờ kết thúc phải sau giờ bắt đầu.')
      return
    }
    setSubmitting(true)
    try {
      const body = { weekday: Number(form.weekday), start_time: form.start_time,
                    end_time: form.end_time, room: form.room }
      if (modalMode === 'create') {
        await api.post('/classes/schedules', { ...body, class_id: Number(form.class_id) })
      } else {
        await api.patch(`/classes/schedules/${editingRow.id}`, body)
      }
      closeModal()
      load()
    } catch (err) {
      setError(err.response?.data?.detail || 'Không lưu được lịch học.')
    } finally {
      setSubmitting(false)
    }
  }

  const remove = async (s) => {
    if (!window.confirm(`Xóa lịch học ${s.class_code} — ${WEEKDAYS[s.weekday]}?`)) return
    try {
      await api.delete(`/classes/schedules/${s.id}`)
      load()
    } catch (err) {
      alert(err.response?.data?.detail || 'Không xóa được lịch học.')
    }
  }

  return (
    <div>
      <div className="admin-toolbar">
        <div className="admin-toolbar-search">
          <MagnifyingGlass size={16} />
          <input
            placeholder="Tìm theo mã lớp, môn học hoặc phòng…"
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
                <th>Thứ</th>
                <th>Giờ</th>
                <th>Phòng</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {rows?.map((s) => (
                <tr key={s.id}>
                  <td>{s.class_code}</td>
                  <td>{s.subject_name}</td>
                  <td>{WEEKDAYS[s.weekday]}</td>
                  <td>{s.start_time.slice(0, 5)}–{s.end_time.slice(0, 5)}</td>
                  <td>{s.room}</td>
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
                  <td colSpan={6} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 24 }}>
                    {debouncedQuery ? 'Không tìm thấy lịch học phù hợp' : 'Chưa có lịch học nào'}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <Pagination page={page} pageSize={PAGE_SIZE} total={total} onPageChange={setPage} />
      </div>

      {modalMode && (
        <Modal title={modalMode === 'create' ? 'Thêm lịch học' : `Sửa lịch học — ${editingRow.class_code}`} onClose={closeModal} width={420}>
          <form onSubmit={submit} className="modal-form" style={{ marginTop: 16 }}>
            {modalMode === 'create' && (
              <div className="field" style={{ gridColumn: '1 / -1' }}>
                <label>Lớp học phần</label>
                <select className="select" required value={form.class_id} onChange={(e) => setForm({ ...form, class_id: e.target.value })}>
                  <option value="">— Chọn lớp —</option>
                  {classes.map((c) => (
                    <option key={c.id} value={c.id}>{c.class_code} — {c.subject_name}</option>
                  ))}
                </select>
              </div>
            )}
            <div className="field">
              <label>Thứ</label>
              <select className="select" value={form.weekday} onChange={(e) => setForm({ ...form, weekday: e.target.value })}>
                {WEEKDAYS.map((w, i) => <option key={i} value={i}>{w}</option>)}
              </select>
            </div>
            <div className="field">
              <label>Phòng</label>
              <input required value={form.room} onChange={(e) => setForm({ ...form, room: e.target.value })} />
            </div>
            <div className="field">
              <label>Giờ bắt đầu</label>
              <input type="time" required value={form.start_time} onChange={(e) => setForm({ ...form, start_time: e.target.value })} />
            </div>
            <div className="field">
              <label>Giờ kết thúc</label>
              <input type="time" required value={form.end_time} onChange={(e) => setForm({ ...form, end_time: e.target.value })} />
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
