import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import Webcam from 'react-webcam'
import { CheckCircle, Question, WarningCircle } from '@phosphor-icons/react'
import api from '../api'

const CAPTURE_INTERVAL_MS = 2000

const BOX_COLOR = { recognized: '#22c55e', already_checked: '#22c55e', spoof: '#ef4444', unknown: '#9ca3af' }

const STATUS_LABEL = {
  present: 'Có mặt', late: 'Muộn', absent: 'Vắng', manual: 'Điểm danh tay',
}

/** Man hinh diem danh theo phien: webcam -> nhan dien moi 2s -> overlay + roster realtime. */
export default function AttendanceScreen() {
  const { sessionId } = useParams()
  const navigate = useNavigate()

  const webcamRef = useRef(null)
  const canvasRef = useRef(null)
  const timerRef = useRef(null)

  const [session, setSession] = useState(null)
  const [roster, setRoster] = useState(null)
  const [records, setRecords] = useState([])
  const [liveResults, setLiveResults] = useState([])
  const [spoofIds, setSpoofIds] = useState(() => new Set())
  const [manualStudentId, setManualStudentId] = useState('')
  const [closing, setClosing] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const { data: s } = await api.get(`/sessions/${sessionId}`)
        if (cancelled) return
        setSession(s)
        const { data: students } = await api.get(`/classes/${s.class_id}/students`)
        if (cancelled) return
        setRoster(students)
        const { data: recs } = await api.get(`/sessions/${sessionId}/records`)
        if (!cancelled) setRecords(recs)
      } catch {
        if (!cancelled) setError('Không tải được thông tin phiên điểm danh.')
      }
    }
    load()
    return () => {
      cancelled = true
    }
  }, [sessionId])

  const refreshRecords = useCallback(async () => {
    const { data } = await api.get(`/sessions/${sessionId}/records`)
    setRecords(data)
  }, [sessionId])

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
        ? `⚠ nghi gia mạo (${r.liveness_score})`
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

  const captureAndSend = useCallback(async () => {
    const shot = webcamRef.current?.getScreenshot()
    if (!shot) return
    const blob = await (await fetch(shot)).blob()
    const form = new FormData()
    form.append('frame', blob, 'frame.jpg')
    try {
      const { data } = await api.post(`/sessions/${sessionId}/recognize`, form)
      setLiveResults(data)
      drawOverlay(data)

      const newSpoofIds = data.filter((r) => r.status === 'spoof' && r.student_id).map((r) => r.student_id)
      if (newSpoofIds.length) {
        setSpoofIds((prev) => new Set([...prev, ...newSpoofIds]))
      }
      if (data.some((r) => r.status === 'recognized')) {
        refreshRecords()
      }
    } catch {
      /* phien da dong hoac loi mang */
    }
  }, [sessionId, drawOverlay, refreshRecords])

  useEffect(() => {
    if (!session || session.status !== 'open') return undefined
    timerRef.current = setInterval(captureAndSend, CAPTURE_INTERVAL_MS)
    return () => clearInterval(timerRef.current)
  }, [session, captureAndSend])

  const recordByStudent = new Map(records.map((r) => [r.student_id, r]))
  const uncheckedStudents = (roster || []).filter((s) => !recordByStudent.has(s.id))

  const submitManual = async (e) => {
    e.preventDefault()
    if (!manualStudentId) return
    await api.post(`/sessions/${sessionId}/manual`, { student_id: Number(manualStudentId) })
    setManualStudentId('')
    refreshRecords()
  }

  const closeSession = async () => {
    setClosing(true)
    try {
      const { data } = await api.patch(`/sessions/${sessionId}/close`)
      clearInterval(timerRef.current)
      alert(`Đã đóng phiên. Có mặt: ${data.present}, vắng: ${data.absent}`)
      navigate(`/sessions/${sessionId}/records`)
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

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <h2 style={{ margin: 0 }}>{session.class_code} — {session.subject_name}</h2>
        <p style={{ margin: '2px 0 0', color: 'var(--text-muted)', fontSize: 13.5 }}>
          Phòng {session.room} · {session.session_date}
          {session.status !== 'open' && <span className="tag tag-neutral" style={{ marginLeft: 8 }}>Đã đóng</span>}
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 480px) 1fr', gap: 20, alignItems: 'start' }}>
        <div className="card" style={{ padding: 16 }}>
          <div style={{ position: 'relative' }}>
            <Webcam ref={webcamRef} screenshotFormat="image/jpeg" width="100%" style={{ borderRadius: 12, display: 'block' }} />
            <canvas
              ref={canvasRef}
              style={{
                position: 'absolute', top: 0, left: 0, width: '100%', height: '100%',
                borderRadius: 12, pointerEvents: 'none',
              }}
            />
          </div>

          {session.status === 'open' && (
            <button className="btn btn-ghost" style={{ marginTop: 12, width: '100%' }} onClick={closeSession} disabled={closing}>
              {closing ? 'Đang đóng…' : 'Đóng phiên & chốt vắng'}
            </button>
          )}

          {session.status === 'open' && uncheckedStudents.length > 0 && (
            <form onSubmit={submitManual} style={{ marginTop: 12, display: 'flex', gap: 8 }}>
              <select
                className="select"
                style={{ flex: 1 }}
                value={manualStudentId}
                onChange={(e) => setManualStudentId(e.target.value)}
              >
                <option value="">— Xác nhận tay cho SV —</option>
                {uncheckedStudents.map((s) => (
                  <option key={s.id} value={s.id}>{s.student_code} — {s.full_name}</option>
                ))}
              </select>
              <button type="submit" className="btn btn-primary" disabled={!manualStudentId}>Xác nhận</button>
            </form>
          )}
        </div>

        <div className="card">
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>MSSV</th>
                  <th>Họ tên</th>
                  <th>Trạng thái</th>
                </tr>
              </thead>
              <tbody>
                {roster.map((s) => {
                  const record = recordByStudent.get(s.id)
                  const isSpoofFlagged = !record && spoofIds.has(s.id)
                  return (
                    <tr key={s.id}>
                      <td>{s.student_code}</td>
                      <td>{s.full_name}</td>
                      <td>
                        {record ? (
                          <span className={`tag ${record.status === 'absent' ? 'tag-danger' : 'tag-success'}`}>
                            {STATUS_LABEL[record.status] || record.status}
                          </span>
                        ) : isSpoofFlagged ? (
                          <span className="tag tag-danger">
                            <WarningCircle size={12} weight="fill" style={{ verticalAlign: -1 }} /> Nghi gian lận
                          </span>
                        ) : (
                          <span className="tag tag-neutral">Chưa điểm danh</span>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {liveResults.length > 0 && (
        <div className="card" style={{ padding: 16, marginTop: 20 }}>
          <h3 style={{ margin: '0 0 12px', fontSize: 14 }}>Frame hiện tại</h3>
          <div style={{ display: 'grid', gap: 8 }}>
            {liveResults.map((r, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13.5 }}>
                {r.status === 'spoof' ? (
                  <>
                    <WarningCircle size={16} color="var(--danger)" weight="fill" />
                    <span style={{ color: 'var(--danger)' }}>
                      Nghi gia mạo{r.full_name ? ` — ${r.student_code} ${r.full_name}` : ' (chưa rõ danh tính)'}
                      {' '}<span className="tag tag-danger">liveness {r.liveness_score}</span>
                    </span>
                  </>
                ) : r.status === 'unknown' ? (
                  <>
                    <Question size={16} color="var(--text-muted)" />
                    <span style={{ color: 'var(--text-muted)' }}>Không nhận diện được (conf {r.confidence})</span>
                  </>
                ) : (
                  <>
                    <CheckCircle size={16} color="var(--success)" weight="fill" />
                    <span>
                      {r.student_code} — {r.full_name} <span className="tag tag-neutral">{r.status}</span>
                    </span>
                  </>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
