import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import Webcam from 'react-webcam'
import { Clock, WarningCircle, ClipboardText } from '@phosphor-icons/react'
import api from '../api'
import ToastStack from '../components/ToastStack'

const INTERVAL_OPTIONS = [1000, 2000, 3000, 5000]
const DEFAULT_INTERVAL_MS = 2000

const BOX_COLOR = {
  recognized: '#22c55e', already_checked: '#22c55e', confirming: '#f59e0b',
  spoof: '#ef4444', unknown: '#9ca3af',
}

const STATUS_META = {
  present: { label: 'Có mặt', tint: 'success' },
  late: { label: 'Muộn', tint: 'warning' },
  manual: { label: 'Điểm danh tay', tint: 'manual' },
}

function formatElapsed(totalSeconds) {
  const pad = (n) => String(n).padStart(2, '0')
  const h = Math.floor(totalSeconds / 3600)
  const m = Math.floor((totalSeconds % 3600) / 60)
  const s = totalSeconds % 60
  return h > 0 ? `${pad(h)}:${pad(m)}:${pad(s)}` : `${pad(m)}:${pad(s)}`
}

/** Man hinh diem danh theo phien: webcam -> nhan dien dinh ky -> overlay + roster realtime. */
export default function AttendanceScreen() {
  const { sessionId } = useParams()

  const webcamRef = useRef(null)
  const canvasRef = useRef(null)
  const captureCanvasRef = useRef(null)
  const timerRef = useRef(null)
  const sendingRef = useRef(false)

  const [session, setSession] = useState(null)
  const [roster, setRoster] = useState(null)
  const [liveResults, setLiveResults] = useState([])
  const [spoofIds, setSpoofIds] = useState(() => new Set())
  const [manualPending, setManualPending] = useState(null)
  const [closing, setClosing] = useState(false)
  const [summary, setSummary] = useState(null)
  const [error, setError] = useState('')
  const [netError, setNetError] = useState('')
  const [intervalMs, setIntervalMs] = useState(DEFAULT_INTERVAL_MS)
  const [elapsed, setElapsed] = useState(0)
  const [toasts, setToasts] = useState([])

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const [{ data: s }, { data: r }] = await Promise.all([
          api.get(`/sessions/${sessionId}`),
          api.get(`/sessions/${sessionId}/roster`),
        ])
        if (cancelled) return
        setSession(s)
        setRoster(r)
      } catch {
        if (!cancelled) setError('Không tải được thông tin phiên điểm danh.')
      }
    }
    load()
    return () => {
      cancelled = true
    }
  }, [sessionId])

  // Dong ho thoi gian phien da mo - chi chay khi phien con "open".
  useEffect(() => {
    if (!session?.opened_at || session.status !== 'open') return undefined
    const start = new Date(session.opened_at).getTime()
    const tick = () => setElapsed(Math.max(0, Math.floor((Date.now() - start) / 1000)))
    tick()
    const id = setInterval(tick, 1000)
    return () => clearInterval(id)
  }, [session?.opened_at, session?.status])

  const pushToast = (message) => {
    const id = `${Date.now()}-${Math.random()}`
    setToasts((prev) => [...prev, { id, message }])
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 4000)
  }

  const drawOverlay = useCallback((results) => {
    const canvas = canvasRef.current
    const video = webcamRef.current?.video
    if (!canvas || !video) return
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    const ctx = canvas.getContext('2d')
    ctx.clearRect(0, 0, canvas.width, canvas.height)

    results.forEach((r) => {
      if (!r.bbox) return
      const [x1, y1, x2, y2] = r.bbox
      const color = BOX_COLOR[r.status] || BOX_COLOR.unknown
      ctx.strokeStyle = color
      ctx.lineWidth = 3
      ctx.strokeRect(x1, y1, x2 - x1, y2 - y1)

      const label = r.status === 'spoof'
        ? `⚠ nghi giả mạo (${r.liveness_score})`
        : r.full_name
          ? `${r.full_name} (${r.confidence})`
          : `? (${r.confidence})`
      ctx.font = '16px sans-serif'
      const textWidth = ctx.measureText(label).width
      ctx.fillStyle = color
      ctx.fillRect(x1, Math.max(y1 - 22, 0), textWidth + 10, 22)
      ctx.fillStyle = '#0a0a0a'
      ctx.fillText(label, x1 + 5, Math.max(y1 - 6, 14))
    })
  }, [])

  // Chup frame bang canvas.toBlob (khong qua base64/dataURL), khoa gui chong bang
  // sendingRef, va bo qua khi tab dang an de tiet kiem bang thong/CPU.
  const captureAndSend = useCallback(async () => {
    if (sendingRef.current || document.visibilityState === 'hidden') return
    if (!session || session.status !== 'open') return
    const video = webcamRef.current?.video
    if (!video || video.readyState < 2) return

    if (!captureCanvasRef.current) captureCanvasRef.current = document.createElement('canvas')
    const canvas = captureCanvasRef.current
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height)

    canvas.toBlob(async (blob) => {
      if (!blob) return
      sendingRef.current = true
      const form = new FormData()
      form.append('frame', blob, 'frame.jpg')
      try {
        const { data } = await api.post(`/sessions/${sessionId}/recognize`, form)
        setLiveResults(data)
        drawOverlay(data)
        setNetError('')

        const newSpoofIds = data.filter((r) => r.status === 'spoof' && r.student_id).map((r) => r.student_id)
        if (newSpoofIds.length) {
          setSpoofIds((prev) => new Set([...prev, ...newSpoofIds]))
        }

        const recognizedIds = data.filter((r) => r.status === 'recognized' && r.student_id).map((r) => r.student_id)
        if (recognizedIds.length) {
          const { data: freshRoster } = await api.get(`/sessions/${sessionId}/roster`)
          setRoster(freshRoster)
          recognizedIds.forEach((id) => {
            const entry = freshRoster.find((row) => row.student_id === id)
            if (entry) {
              const label = STATUS_META[entry.status]?.label || entry.status
              pushToast(`✓ ${entry.full_name} — ${label} (${entry.confidence?.toFixed(2)})`)
            }
          })
        }
      } catch {
        // Loi mang khong duoc chan UI - chi bao hieu nhe, lan chup ke tiep se tu thu lai.
        setNetError('Mất kết nối với máy chủ, đang thử lại ở lần chụp sau…')
      } finally {
        sendingRef.current = false
      }
    }, 'image/jpeg', 0.8)
  }, [session, sessionId, drawOverlay])

  useEffect(() => {
    if (!session || session.status !== 'open') return undefined
    timerRef.current = setInterval(captureAndSend, intervalMs)
    return () => clearInterval(timerRef.current)
  }, [session, captureAndSend, intervalMs])

  const manualCheck = async (studentId) => {
    setManualPending(studentId)
    try {
      await api.post(`/sessions/${sessionId}/manual`, { student_id: studentId })
      const { data: freshRoster } = await api.get(`/sessions/${sessionId}/roster`)
      setRoster(freshRoster)
    } catch (err) {
      alert(err.response?.data?.detail || 'Không xác nhận được.')
    } finally {
      setManualPending(null)
    }
  }

  const requestClose = () => {
    if (!window.confirm('Đóng phiên điểm danh? Sinh viên chưa điểm danh sẽ được ghi nhận vắng.')) return
    closeSession()
  }

  const closeSession = async () => {
    setClosing(true)
    try {
      const { data } = await api.patch(`/sessions/${sessionId}/close`)
      clearInterval(timerRef.current)
      setSession((s) => ({ ...s, status: 'closed' }))
      setSummary(data)
      const { data: freshRoster } = await api.get(`/sessions/${sessionId}/roster`)
      setRoster(freshRoster)
    } finally {
      setClosing(false)
    }
  }

  if (error) {
    return <div className="card empty-state"><p>{error}</p></div>
  }

  if (!session || !roster) {
    return <div className="card skeleton" style={{ height: 300 }} />
  }

  const presentCount = roster.filter((r) => r.status === 'present' || r.status === 'manual').length
  const lateCount = roster.filter((r) => r.status === 'late').length
  const uncheckedCount = roster.filter((r) => !r.status).length

  return (
    <div>
      <ToastStack toasts={toasts} />

      <div className="session-topbar">
        <div>
          <h2 style={{ margin: 0 }}>{session.class_code} — {session.subject_name}</h2>
          <p style={{ margin: '2px 0 0', color: 'var(--text-muted)', fontSize: 13.5 }}>
            Phòng {session.room} · {session.session_date} · {session.start_time}–{session.end_time}
            {session.status !== 'open' && <span className="tag tag-neutral" style={{ marginLeft: 8 }}>Đã đóng</span>}
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          {session.status === 'open' && (
            <span className="session-clock"><Clock size={14} weight="bold" /> {formatElapsed(elapsed)}</span>
          )}
          {session.status === 'open' && (
            <button className="btn btn-primary" onClick={requestClose} disabled={closing}>
              {closing ? 'Đang đóng…' : 'Đóng phiên'}
            </button>
          )}
        </div>
      </div>

      <div className="attendance-layout">
        <div className="card" style={{ padding: 16 }}>
          <div className="video-frame">
            <Webcam ref={webcamRef} screenshotFormat="image/jpeg" />
            <canvas ref={canvasRef} className="overlay-canvas" />
          </div>

          {session.status === 'open' && (
            <div className="capture-controls">
              <label>
                Chụp mỗi
                <select className="select" value={intervalMs} onChange={(e) => setIntervalMs(Number(e.target.value))}>
                  {INTERVAL_OPTIONS.map((ms) => (
                    <option key={ms} value={ms}>{ms / 1000} giây</option>
                  ))}
                </select>
              </label>
            </div>
          )}

          {netError && <div className="net-error-banner">{netError}</div>}

          {liveResults.length > 0 && (
            <div style={{ marginTop: 16 }}>
              <h3 style={{ margin: '0 0 10px', fontSize: 13.5 }}>Frame hiện tại</h3>
              <div style={{ display: 'grid', gap: 6 }}>
                {liveResults.map((r, i) => (
                  <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12.5 }}>
                    {r.status === 'spoof' ? (
                      <span style={{ color: 'var(--danger)' }}>
                        <WarningCircle size={14} weight="fill" style={{ verticalAlign: -2 }} />{' '}
                        Nghi giả mạo{r.full_name ? ` — ${r.student_code} ${r.full_name}` : ''}
                      </span>
                    ) : r.status === 'unknown' ? (
                      <span style={{ color: 'var(--text-muted)' }}>Không nhận diện được (conf {r.confidence})</span>
                    ) : r.status === 'confirming' ? (
                      <span style={{ color: 'var(--warning)' }}>
                        {r.full_name} — đang xác nhận ({r.confirm_count}/{r.confirm_needed})
                      </span>
                    ) : (
                      <span>{r.student_code} — {r.full_name} <span className="tag tag-neutral">{r.status}</span></span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="card">
          <div className="roster-counter">
            <span><span className="roster-dot" style={{ background: 'var(--success)' }} /> Có mặt {presentCount}/{roster.length}</span>
            <span><span className="roster-dot" style={{ background: 'var(--warning)' }} /> Muộn {lateCount}</span>
            <span><span className="roster-dot" style={{ background: 'var(--text-muted)' }} /> Chưa {uncheckedCount}</span>
          </div>

          {roster.length ? (
            <div>
              {roster.map((entry) => {
                const meta = STATUS_META[entry.status]
                const isSpoofFlagged = !entry.status && spoofIds.has(entry.student_id)
                return (
                  <div key={entry.student_id} className="roster-row">
                    <div className="roster-row-name">
                      <strong>{entry.full_name}</strong>
                      <span>{entry.student_code}</span>
                    </div>
                    {meta ? (
                      <span className={`tag tag-${meta.tint}`}>{meta.label}</span>
                    ) : isSpoofFlagged ? (
                      <span className="tag tag-danger tag-blink">
                        <WarningCircle size={12} weight="fill" style={{ verticalAlign: -1 }} /> Nghi gian lận
                      </span>
                    ) : session.status === 'open' ? (
                      <button
                        className="btn btn-ghost"
                        style={{ padding: '5px 10px', fontSize: 12 }}
                        onClick={() => manualCheck(entry.student_id)}
                        disabled={manualPending === entry.student_id}
                      >
                        {manualPending === entry.student_id ? 'Đang xác nhận…' : 'Xác nhận tay'}
                      </button>
                    ) : (
                      <span className="tag tag-neutral">Chưa điểm danh</span>
                    )}
                  </div>
                )
              })}
            </div>
          ) : (
            <div className="empty-state">
              <ClipboardText size={28} />
              <p>Lớp này chưa có sinh viên ghi danh.</p>
            </div>
          )}
        </div>
      </div>

      {summary && (
        <div className="modal-overlay" onClick={() => setSummary(null)}>
          <div className="card modal-card" onClick={(e) => e.stopPropagation()}>
            <h3 style={{ margin: 0 }}>Đã đóng phiên điểm danh</h3>
            <div className="modal-summary-grid">
              <div>
                <span className="modal-summary-value" style={{ color: 'var(--success)' }}>{summary.present}</span>
                <span className="modal-summary-label">Có mặt</span>
              </div>
              <div>
                <span className="modal-summary-value" style={{ color: 'var(--danger)' }}>{summary.absent}</span>
                <span className="modal-summary-label">Vắng</span>
              </div>
              <div>
                <span className="modal-summary-value" style={{ color: 'var(--warning)' }}>{summary.newly_warned?.length || 0}</span>
                <span className="modal-summary-label">Mới cảnh báo</span>
              </div>
            </div>
            {summary.newly_warned?.length > 0 && (
              <p style={{ fontSize: 12.5, color: 'var(--text-muted)', margin: 0 }}>
                {summary.newly_warned.map((w) => w.full_name).join(', ')} vừa vượt ngưỡng vắng.
              </p>
            )}
            <div style={{ display: 'flex', gap: 10 }}>
              <Link
                to={`/sessions/${sessionId}/records`}
                className="btn btn-primary"
                style={{ flex: 1, textAlign: 'center' }}
              >
                Xem chi tiết điểm danh
              </Link>
              <button className="btn btn-ghost" onClick={() => setSummary(null)}>Đóng</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
