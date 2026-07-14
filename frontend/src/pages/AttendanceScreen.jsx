import { useCallback, useRef, useState } from 'react'
import Webcam from 'react-webcam'
import { CheckCircle, Question, WarningCircle } from '@phosphor-icons/react'
import api from '../api'
import { API_BASE_URL as API_BASE } from '../config'

/** Man hinh diem danh: mo phien -> webcam gui frame moi 2 giay -> hien ket qua. */
export default function AttendanceScreen() {
  const webcamRef = useRef(null)
  const timerRef = useRef(null)
  const sessionIdRef = useRef(null)
  const [scheduleId, setScheduleId] = useState('')
  const [session, setSession] = useState(null)
  const [results, setResults] = useState([])
  const [log, setLog] = useState([])
  const [spoofLog, setSpoofLog] = useState([])

  const captureAndSend = useCallback(async () => {
    const shot = webcamRef.current?.getScreenshot()
    if (!shot || !sessionIdRef.current) return
    const blob = await (await fetch(shot)).blob()
    const form = new FormData()
    form.append('frame', blob, 'frame.jpg')
    try {
      const { data } = await api.post(`/sessions/${sessionIdRef.current}/recognize`, form)
      setResults(data)
      data
        .filter((r) => r.status === 'recognized')
        .forEach((r) => setLog((prev) => [r, ...prev]))
      data
        .filter((r) => r.status === 'spoof')
        .forEach((r) => setSpoofLog((prev) => [{ ...r, time: new Date().toLocaleTimeString() }, ...prev]))
    } catch {
      /* phien da dong hoac loi mang */
    }
  }, [])

  const openSession = async () => {
    const { data } = await api.post('/sessions', {
      schedule_id: Number(scheduleId),
      session_date: new Date().toISOString().slice(0, 10),
    })
    sessionIdRef.current = data.id
    setSession(data)
    timerRef.current = setInterval(captureAndSend, 2000)
  }

  const closeSession = async () => {
    clearInterval(timerRef.current)
    const { data } = await api.patch(`/sessions/${session.id}/close`)
    alert(`Đã đóng phiên. Có mặt: ${data.present}, vắng: ${data.absent}`)
    sessionIdRef.current = null
    setSession(null)
    setResults([])
  }

  if (!session) {
    return (
      <div className="card" style={{ padding: 24, maxWidth: 420 }}>
        <h3 style={{ marginTop: 0 }}>Mở phiên điểm danh</h3>
        <div className="field" style={{ marginBottom: 16 }}>
          <label htmlFor="scheduleId">Schedule ID</label>
          <input
            id="scheduleId"
            placeholder="vd: 1"
            value={scheduleId}
            onChange={(e) => setScheduleId(e.target.value)}
          />
        </div>
        <button className="btn btn-primary" onClick={openSession} disabled={!scheduleId}>
          Mở phiên điểm danh
        </button>
      </div>
    )
  }

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 480px) 1fr', gap: 20, alignItems: 'start' }}>
      <div className="card" style={{ padding: 16 }}>
        <Webcam ref={webcamRef} screenshotFormat="image/jpeg" width="100%" style={{ borderRadius: 12 }} />
        <button className="btn btn-ghost" style={{ marginTop: 12, width: '100%' }} onClick={closeSession}>
          Đóng phiên &amp; chốt vắng
        </button>
      </div>

      <div style={{ display: 'grid', gap: 16 }}>
        <div className="card" style={{ padding: 16 }}>
          <h3 style={{ margin: '0 0 12px', fontSize: 14 }}>Frame hiện tại</h3>
          {results.length ? (
            <div style={{ display: 'grid', gap: 8 }}>
              {results.map((r, i) => (
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
          ) : (
            <p style={{ color: 'var(--text-muted)', fontSize: 13.5, margin: 0 }}>Đang chờ khung hình đầu tiên…</p>
          )}
        </div>

        {spoofLog.length > 0 && (
          <div className="card spoof-alert" style={{ padding: 16 }}>
            <h3 style={{ margin: '0 0 12px', fontSize: 14, color: 'var(--danger)' }}>
              <WarningCircle size={16} weight="fill" style={{ verticalAlign: -2, marginRight: 6 }} />
              Cảnh báo gian lận ({spoofLog.length})
            </h3>
            <div style={{ display: 'grid', gap: 8 }}>
              {spoofLog.map((s, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  {s.evidence_image && (
                    <img
                      src={`${API_BASE}${s.evidence_image}`}
                      width={44}
                      height={44}
                      style={{ objectFit: 'cover', borderRadius: 8, border: '1px solid var(--danger)' }}
                      alt={`Ảnh bằng chứng nghi gian lận${s.full_name ? ` của ${s.full_name}` : ''}`}
                    />
                  )}
                  <span style={{ fontSize: 13.5 }}>
                    {s.time} —{' '}
                    {s.full_name ? `${s.student_code} — ${s.full_name}` : 'Chưa rõ danh tính'}{' '}
                    <span className="tag tag-danger">liveness {s.liveness_score}</span>
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="card" style={{ padding: 16 }}>
          <h3 style={{ margin: '0 0 12px', fontSize: 14 }}>Đã điểm danh</h3>
          {log.length ? (
            <div style={{ display: 'grid', gap: 8 }}>
              {log.map((l, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  {l.evidence_image && (
                    <img
                      src={`${API_BASE}${l.evidence_image}`}
                      width={44}
                      height={44}
                      style={{ objectFit: 'cover', borderRadius: 8, border: '1px solid var(--border)' }}
                      alt={`Ảnh bằng chứng điểm danh của ${l.full_name}`}
                    />
                  )}
                  <span style={{ fontSize: 13.5 }}>
                    {l.student_code} — {l.full_name} <span className="tag tag-success">{l.confidence}</span>
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p style={{ color: 'var(--text-muted)', fontSize: 13.5, margin: 0 }}>Chưa có sinh viên nào được ghi nhận.</p>
          )}
        </div>
      </div>
    </div>
  )
}
