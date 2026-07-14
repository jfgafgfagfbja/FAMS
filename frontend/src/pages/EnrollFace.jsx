import { useEffect, useRef, useState } from 'react'
import Webcam from 'react-webcam'
import { Camera } from '@phosphor-icons/react'
import api from '../api'

const POSES = ['Nhìn thẳng', 'Nghiêng trái', 'Nghiêng phải', 'Ngẩng nhẹ', 'Cúi nhẹ']
const role = sessionStorage.getItem('role')

/** Dang ky khuon mat: xac nhan dong y -> chup 5 anh theo huong dan -> gui len /faces/enroll. */
export default function EnrollFace() {
  const webcamRef = useRef(null)
  const [studentId, setStudentId] = useState('')
  const [student, setStudent] = useState(null)
  const [lookupError, setLookupError] = useState('')
  const [shots, setShots] = useState([])
  const [message, setMessage] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [consenting, setConsenting] = useState(false)

  useEffect(() => {
    if (role === 'student') {
      api.get('/students/me').then(({ data }) => {
        setStudent(data)
        setStudentId(String(data.id))
      })
    }
  }, [])

  const lookupStudent = async () => {
    setLookupError('')
    setStudent(null)
    try {
      const { data } = await api.get(`/students/${studentId}`)
      setStudent(data)
    } catch {
      setLookupError('Không tìm thấy sinh viên với ID này.')
    }
  }

  const giveConsent = async () => {
    setConsenting(true)
    try {
      await api.post(`/students/${studentId}/consent`)
      setStudent((s) => ({ ...s, consent_given: true }))
    } catch {
      setLookupError('Không thể xác nhận đồng ý (có thể cần sinh viên hoặc admin xác nhận).')
    } finally {
      setConsenting(false)
    }
  }

  const capture = () => {
    const shot = webcamRef.current?.getScreenshot()
    if (shot) setShots((prev) => [...prev, shot])
  }

  const submit = async () => {
    setSubmitting(true)
    setMessage('')
    try {
      const form = new FormData()
      for (let i = 0; i < shots.length; i++) {
        const blob = await (await fetch(shots[i])).blob()
        form.append('images', blob, `pose_${i}.jpg`)
      }
      const { data } = await api.post(`/faces/enroll/${studentId}`, form)
      setMessage(data.message)
      if (data.ok) setShots([])
    } finally {
      setSubmitting(false)
    }
  }

  const canCapture = student?.consent_given

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 420px) 1fr', gap: 20, alignItems: 'start' }}>
      <div className="card" style={{ padding: 16 }}>
        {role !== 'student' && (
          <div className="field" style={{ marginBottom: 12 }}>
            <label htmlFor="studentId">Student ID</label>
            <div style={{ display: 'flex', gap: 8 }}>
              <input
                id="studentId"
                placeholder="vd: 1"
                value={studentId}
                onChange={(e) => setStudentId(e.target.value)}
              />
              <button className="btn btn-ghost" onClick={lookupStudent} disabled={!studentId}>
                Tra cứu
              </button>
            </div>
          </div>
        )}

        {lookupError && <p className="field-error" style={{ marginBottom: 12 }}>{lookupError}</p>}

        {student && (
          <div
            className="card"
            style={{ padding: 12, marginBottom: 12, background: 'var(--surface-hover)', border: 'none' }}
          >
            <p style={{ margin: 0, fontSize: 13.5 }}>
              <strong>{student.full_name}</strong> — {student.student_code}
            </p>
            {student.consent_given ? (
              <span className="tag tag-success" style={{ marginTop: 6 }}>Đã đồng ý thu thập dữ liệu khuôn mặt</span>
            ) : (
              <div style={{ marginTop: 8 }}>
                <p style={{ margin: '0 0 8px', fontSize: 13, color: 'var(--text-muted)' }}>
                  Sinh viên chưa xác nhận đồng ý cho phép FAMS thu thập dữ liệu khuôn mặt để điểm danh.
                  {role === 'lecturer' && ' Giảng viên không thể xác nhận thay — cần sinh viên tự đăng nhập xác nhận hoặc admin xác nhận hộ.'}
                </p>
                {(role === 'admin' || role === 'student') && (
                  <button className="btn btn-primary" onClick={giveConsent} disabled={consenting}>
                    {consenting ? 'Đang xác nhận…' : 'Tôi đồng ý / Xác nhận đồng ý'}
                  </button>
                )}
              </div>
            )}
          </div>
        )}

        {canCapture ? (
          <>
            <Webcam ref={webcamRef} screenshotFormat="image/jpeg" width="100%" style={{ borderRadius: 12 }} />

            <p style={{ margin: '10px 0', fontSize: 13.5, color: 'var(--text-muted)' }}>
              <strong style={{ color: 'var(--text)' }}>{POSES[shots.length] || 'Đủ ảnh, hãy gửi'}</strong> ({shots.length}/5)
            </p>

            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <button className="btn btn-primary" onClick={capture} disabled={shots.length >= 5}>
                <Camera size={16} weight="bold" /> Chụp
              </button>
              <button className="btn btn-ghost" onClick={submit} disabled={shots.length < 3 || submitting}>
                {submitting ? 'Đang gửi…' : `Gửi đăng ký (${shots.length} ảnh)`}
              </button>
              <button className="btn btn-ghost" onClick={() => setShots([])} disabled={!shots.length}>
                Chụp lại
              </button>
            </div>

            {message && <p style={{ marginTop: 12, fontSize: 13, color: 'var(--text-muted)' }}>{message}</p>}
          </>
        ) : (
          <div className="empty-state">
            <p>
              {student
                ? 'Cần xác nhận đồng ý ở trên trước khi chụp ảnh.'
                : role === 'student'
                  ? 'Đang tải hồ sơ của bạn…'
                  : 'Nhập Student ID và bấm "Tra cứu" để bắt đầu.'}
            </p>
          </div>
        )}
      </div>

      <div className="card" style={{ padding: 16 }}>
        <h3 style={{ margin: '0 0 12px', fontSize: 14 }}>Ảnh đã chụp</h3>
        {shots.length ? (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(120px, 1fr))', gap: 10 }}>
            {shots.map((s, i) => (
              <img
                key={i}
                src={s}
                style={{ width: '100%', aspectRatio: '1', objectFit: 'cover', borderRadius: 10, border: '1px solid var(--border)' }}
                alt={`Ảnh khuôn mặt tư thế ${POSES[i] || i + 1}`}
              />
            ))}
          </div>
        ) : (
          <div className="empty-state">
            <p>Chưa có ảnh nào.</p>
          </div>
        )}
      </div>
    </div>
  )
}
