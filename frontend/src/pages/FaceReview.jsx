import { useEffect, useState } from 'react'
import { Check, FingerprintSimple, UserCircle, WarningCircle, X } from '@phosphor-icons/react'
import api from '../api'
import { API_BASE_URL } from '../config'

/** Duyet khuon mat (admin): luoi the SV dang cho duyet, canh bao trung SV khac,
 * duyet 1 cham / tu choi kem ly do bat buoc. */
export default function FaceReview() {
  const [pending, setPending] = useState(null)
  const [rejectingId, setRejectingId] = useState(null)
  const [reason, setReason] = useState('')
  const [busyId, setBusyId] = useState(null)

  const load = () => api.get('/faces/pending').then(({ data }) => setPending(data))

  useEffect(() => {
    load()
  }, [])

  const approve = async (id) => {
    setBusyId(id)
    try {
      await api.patch(`/faces/${id}/approve`)
      setPending((list) => list.filter((p) => p.id !== id))
    } finally {
      setBusyId(null)
    }
  }

  const confirmReject = async (id) => {
    if (!reason.trim()) return
    setBusyId(id)
    try {
      await api.patch(`/faces/${id}/reject`, { reason: reason.trim() })
      setPending((list) => list.filter((p) => p.id !== id))
      setRejectingId(null)
      setReason('')
    } finally {
      setBusyId(null)
    }
  }

  if (pending === null) {
    return <div className="card skeleton" style={{ height: 300 }} />
  }

  if (!pending.length) {
    return (
      <div className="card empty-state">
        <FingerprintSimple size={32} />
        <p>Không có yêu cầu đăng ký khuôn mặt nào đang chờ duyệt.</p>
      </div>
    )
  }

  return (
    <div className="approval-grid">
      {pending.map((p) => (
        <div className="card approval-card" key={p.id}>
          <div className="approval-card-image">
            {p.source_image ? (
              <img src={`${API_BASE_URL}${p.source_image}`} alt={`Ảnh đăng ký của ${p.full_name}`} />
            ) : (
              <UserCircle size={48} weight="light" />
            )}
          </div>

          <div className="approval-card-body">
            <strong>{p.full_name}</strong>
            <span>{p.student_code}</span>
            <span className="approval-card-time">{new Date(p.created_at).toLocaleString()}</span>
            {p.duplicate_warning && (
              <span
                className="tag tag-danger"
                style={{ alignSelf: 'flex-start', marginTop: 2 }}
                title={`Độ tương đồng ${p.duplicate_similarity}`}
              >
                <WarningCircle size={12} weight="fill" style={{ verticalAlign: -1 }} />{' '}
                Trùng với SV {p.duplicate_student_code}
              </span>
            )}
          </div>

          {rejectingId === p.id ? (
            <div className="approval-reject-form">
              <textarea
                placeholder="Lý do từ chối…"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                rows={2}
              />
              <div style={{ display: 'flex', gap: 8 }}>
                <button
                  className="btn btn-primary"
                  style={{ flex: 1 }}
                  onClick={() => confirmReject(p.id)}
                  disabled={!reason.trim() || busyId === p.id}
                >
                  Xác nhận từ chối
                </button>
                <button
                  className="btn btn-ghost"
                  onClick={() => { setRejectingId(null); setReason('') }}
                  disabled={busyId === p.id}
                >
                  Hủy
                </button>
              </div>
            </div>
          ) : (
            <div className="approval-card-actions">
              <button className="btn btn-primary" onClick={() => approve(p.id)} disabled={busyId === p.id}>
                <Check size={15} weight="bold" /> Duyệt
              </button>
              <button className="btn btn-ghost" onClick={() => setRejectingId(p.id)} disabled={busyId === p.id}>
                <X size={15} weight="bold" /> Từ chối
              </button>
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
