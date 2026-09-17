import { useEffect, useRef, useState } from 'react'
import { useLocation, useNavigate, useParams } from 'react-router-dom'
import Webcam from 'react-webcam'
import { Camera, CheckCircle, MapPin, MapPinLine, WarningCircle, XCircle } from '@phosphor-icons/react'
import api from '../api'

const RESULT_META = {
  recognized: { icon: CheckCircle, tint: 'success', title: 'Điểm danh thành công' },
  already_checked: { icon: CheckCircle, tint: 'success', title: 'Bạn đã điểm danh buổi này' },
  not_matched: { icon: XCircle, tint: 'danger', title: 'Không khớp khuôn mặt' },
  no_face: { icon: WarningCircle, tint: 'warning', title: 'Không tìm thấy khuôn mặt' },
  multiple_faces: { icon: WarningCircle, tint: 'warning', title: 'Có nhiều hơn 1 khuôn mặt' },
  spoof: { icon: XCircle, tint: 'danger', title: 'Ảnh nghi giả mạo' },
}

const RECORD_STATUS_LABEL = { present: 'Có mặt', late: 'Muộn' }

/** SV tu chup 1 anh selfie de diem danh - khac luong GV quet camera ca lop:
 * xin vi tri GPS tu trinh duyet (SV co the tu choi, van diem danh duoc nhung
 * khong kem vi tri), chup anh, gui POST /sessions/{id}/self-checkin - backend
 * chi so khop voi khuon mat CHINH SV dang dang nhap (khong so voi ca lop). */
export default function SelfCheckin() {
  const { sessionId } = useParams()
  const location = useLocation()
  const navigate = useNavigate()
  const webcamRef = useRef(null)
  const info = location.state || {}

  // geo: null = dang xin quyen, 'denied'/'unsupported' = khong lay duoc, object = da co toa do
  const [geo, setGeo] = useState(null)
  const [shot, setShot] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!navigator.geolocation) {
      setGeo('unsupported')
      return
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => setGeo({
        latitude: pos.coords.latitude,
        longitude: pos.coords.longitude,
        accuracy: pos.coords.accuracy,
      }),
      () => setGeo('denied'),
      { enableHighAccuracy: true, timeout: 10000 },
    )
  }, [])

  const capture = () => {
    const dataUrl = webcamRef.current?.getScreenshot()
    if (dataUrl) setShot(dataUrl)
  }

  const retake = () => {
    setShot(null)
    setResult(null)
    setError('')
  }

  const submit = async () => {
    if (!shot) return
    setSubmitting(true)
    setError('')
    try {
      const blob = await (await fetch(shot)).blob()
      const form = new FormData()
      form.append('frame', blob, 'selfie.jpg')
      if (geo && typeof geo === 'object') {
        form.append('latitude', String(geo.latitude))
        form.append('longitude', String(geo.longitude))
        form.append('accuracy', String(geo.accuracy))
      }
      const { data } = await api.post(`/sessions/${sessionId}/self-checkin`, form)
      setResult(data)
    } catch (err) {
      setError(err.response?.data?.detail || 'Không gửi được điểm danh, vui lòng thử lại.')
    } finally {
      setSubmitting(false)
    }
  }

  const meta = result ? RESULT_META[result.status] : null
  const ResultIcon = meta?.icon

  return (
    <div className="card" style={{ padding: 20, maxWidth: 460, margin: '0 auto' }}>
      {(info.classCode || info.subjectName) && (
        <p style={{ textAlign: 'center', margin: '0 0 12px', fontSize: 13.5, color: 'var(--text-muted)' }}>
          {info.classCode} — {info.subjectName}{info.room ? ` · P.${info.room}` : ''}
        </p>
      )}

      <div
        className="tag"
        style={{
          display: 'inline-flex', gap: 6, marginBottom: 14,
          background: geo && typeof geo === 'object' ? 'var(--success-soft, var(--surface-hover))' : 'var(--surface-hover)',
        }}
      >
        {geo && typeof geo === 'object' ? (
          <><MapPin size={13} weight="fill" /> Đã lấy vị trí (độ chính xác ~{Math.round(geo.accuracy)}m)</>
        ) : geo === 'denied' ? (
          <><MapPinLine size={13} /> Không có quyền vị trí — vẫn điểm danh được, chỉ thiếu vị trí</>
        ) : geo === 'unsupported' ? (
          <><MapPinLine size={13} /> Trình duyệt không hỗ trợ định vị</>
        ) : (
          <><MapPinLine size={13} /> Đang lấy vị trí…</>
        )}
      </div>

      {!result && (
        <>
          <div className="video-frame">
            {shot ? (
              <img src={shot} alt="Ảnh vừa chụp" style={{ width: '100%', borderRadius: 12 }} />
            ) : (
              <>
                <Webcam ref={webcamRef} screenshotFormat="image/jpeg" mirrored />
                <div className="face-guide" />
              </>
            )}
          </div>

          {error && <p className="field-error" style={{ marginTop: 12, textAlign: 'center' }}>{error}</p>}

          <div style={{ display: 'flex', gap: 10, justifyContent: 'center', marginTop: 16 }}>
            {!shot && (
              <button className="btn btn-primary" onClick={capture}>
                <Camera size={16} weight="bold" /> Chụp
              </button>
            )}
            {shot && (
              <>
                <button className="btn btn-ghost" onClick={retake} disabled={submitting}>Chụp lại</button>
                <button className="btn btn-primary" onClick={submit} disabled={submitting}>
                  {submitting ? 'Đang gửi…' : 'Gửi điểm danh'}
                </button>
              </>
            )}
          </div>
        </>
      )}

      {result && (
        <div className="empty-state">
          <ResultIcon size={40} weight="fill" color={`var(--${meta.tint === 'success' ? 'success' : meta.tint === 'warning' ? 'warning' : 'danger'})`} />
          <p style={{ fontWeight: 700, fontSize: 15, color: 'var(--text)' }}>{meta.title}</p>
          {result.record_status && (
            <span className={`tag tag-${result.record_status === 'late' ? 'warning' : 'success'}`}>
              {RECORD_STATUS_LABEL[result.record_status]}
            </span>
          )}
          {result.message && <p style={{ marginTop: 8 }}>{result.message}</p>}
          <div style={{ display: 'flex', gap: 10, marginTop: 8 }}>
            {(result.status === 'not_matched' || result.status === 'no_face' || result.status === 'multiple_faces' || result.status === 'spoof') && (
              <button className="btn btn-primary" onClick={retake}>Thử lại</button>
            )}
            <button className="btn btn-ghost" onClick={() => navigate('/schedule')}>Về lịch học</button>
          </div>
        </div>
      )}
    </div>
  )
}
