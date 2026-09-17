import { useEffect, useRef, useState } from 'react'
import Webcam from 'react-webcam'
import { Camera, Check, CheckCircle, HourglassMedium } from '@phosphor-icons/react'
import api from '../api'

const role = sessionStorage.getItem('role')

const STEPS = [
  { key: 'consent', label: 'Đồng ý điều khoản' },
  { key: 'front', label: 'Chụp thẳng' },
  { key: 'left', label: 'Nghiêng trái' },
  { key: 'right', label: 'Nghiêng phải' },
]

const POSE_INSTRUCTIONS = {
  front: 'Nhìn thẳng vào camera, giữ khuôn mặt trong khung hình bầu dục.',
  left: 'Nghiêng đầu nhẹ sang trái, vẫn giữ mặt trong khung hình.',
  right: 'Nghiêng đầu nhẹ sang phải, vẫn giữ mặt trong khung hình.',
}

export default function EnrollFace() {
  return role === 'student' ? <SelfEnrollWizard /> : <AdminLookupEnroll />
}

/** Stepper 4 buoc de chinh SV tu dang ky khuon mat: dong y dieu khoan -> chup
 * thang -> nghieng trai -> nghieng phai. Moi anh gui ngay len backend, loi (mo,
 * toi, trung SV khac...) hien tai buoc do, chup lai khong mat cac buoc truoc. */
function SelfEnrollWizard() {
  const webcamRef = useRef(null)
  const [me, setMe] = useState(null)
  const [step, setStep] = useState(0)
  const [consentChecked, setConsentChecked] = useState(false)
  const [submittingConsent, setSubmittingConsent] = useState(false)
  const [shotPreview, setShotPreview] = useState(null)
  const [stepDone, setStepDone] = useState(false)
  const [stepError, setStepError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [successCount, setSuccessCount] = useState(0)

  useEffect(() => {
    api.get('/students/me').then(({ data }) => {
      setMe(data)
      setStep(data.consent_given ? 1 : 0)
    })
  }, [])

  const submitConsent = async () => {
    setSubmittingConsent(true)
    try {
      await api.post(`/students/${me.id}/consent`)
      setMe((m) => ({ ...m, consent_given: true }))
      setStep(1)
    } finally {
      setSubmittingConsent(false)
    }
  }

  const capture = () => {
    const shot = webcamRef.current?.getScreenshot()
    if (shot) submitShot(shot)
  }

  const submitShot = async (dataUrl) => {
    setShotPreview(dataUrl)
    setSubmitting(true)
    setStepError('')
    try {
      const blob = await (await fetch(dataUrl)).blob()
      const form = new FormData()
      form.append('images', blob, `${STEPS[step].key}.jpg`)
      const { data } = await api.post(`/faces/enroll/${me.id}`, form)
      if (data.ok) {
        setStepDone(true)
        setSuccessCount((c) => c + 1)
      } else {
        setStepError(data.message)
      }
    } catch (err) {
      setStepError(err.response?.data?.detail || 'Không gửi được ảnh, vui lòng thử lại.')
    } finally {
      setSubmitting(false)
    }
  }

  const retake = () => {
    setShotPreview(null)
    setStepDone(false)
    setStepError('')
  }

  const nextStep = () => {
    setStep((s) => s + 1)
    setShotPreview(null)
    setStepDone(false)
    setStepError('')
  }

  if (!me) {
    return <div className="card skeleton" style={{ height: 320 }} />
  }

  return (
    <div>
      <div className="stepper">
        {STEPS.map((s, i) => (
          <div key={s.key} className={`stepper-item${i === step ? ' active' : ''}${i < step ? ' done' : ''}`}>
            <span className="stepper-dot">{i < step ? <Check size={14} weight="bold" /> : i + 1}</span>
            <span className="stepper-label">{s.label}</span>
          </div>
        ))}
      </div>

      {step === 0 && (
        <div className="card" style={{ padding: 24, maxWidth: 560, margin: '0 auto' }}>
          <h3 style={{ marginTop: 0 }}>Đồng ý sử dụng dữ liệu khuôn mặt</h3>
          <ul className="consent-list">
            <li>Dữ liệu khuôn mặt của bạn chỉ được dùng để điểm danh tự động tại các buổi học.</li>
            <li>Hệ thống lưu một vector đặc trưng khuôn mặt (embedding). Ảnh khuôn mặt bạn chụp chỉ được lưu tạm để cán bộ đối chiếu khi duyệt và bị xóa ngay sau khi duyệt.</li>
            <li>Ảnh chụp làm bằng chứng khi điểm danh (nếu có) chỉ được lưu trong một thời gian nhất định rồi tự động xóa.</li>
            <li>Dữ liệu vừa đăng ký cần quản trị viên duyệt trước khi có hiệu lực nhận diện.</li>
          </ul>
          <label className="consent-checkbox">
            <input type="checkbox" checked={consentChecked} onChange={(e) => setConsentChecked(e.target.checked)} />
            Tôi đã đọc và đồng ý cho phép FAMS thu thập, xử lý dữ liệu khuôn mặt của tôi theo mục đích trên.
          </label>
          <button
            className="btn btn-primary"
            style={{ marginTop: 16 }}
            disabled={!consentChecked || submittingConsent}
            onClick={submitConsent}
          >
            {submittingConsent ? 'Đang xử lý…' : 'Tôi đồng ý và tiếp tục'}
          </button>
        </div>
      )}

      {step >= 1 && step <= 3 && (
        <div className="card" style={{ padding: 20, maxWidth: 460, margin: '0 auto' }}>
          <p style={{ textAlign: 'center', fontSize: 13.5, color: 'var(--text-muted)', marginTop: 0 }}>
            {POSE_INSTRUCTIONS[STEPS[step].key]}
          </p>

          <div className="video-frame">
            {shotPreview ? (
              <img src={shotPreview} alt="Ảnh vừa chụp" style={{ width: '100%', borderRadius: 12 }} />
            ) : (
              <>
                <Webcam ref={webcamRef} screenshotFormat="image/jpeg" mirrored />
                <div className="face-guide" />
              </>
            )}
          </div>

          {stepError && <p className="field-error" style={{ marginTop: 12, textAlign: 'center' }}>{stepError}</p>}
          {submitting && (
            <p style={{ textAlign: 'center', fontSize: 12.5, color: 'var(--text-muted)', marginTop: 8 }}>
              Đang kiểm tra ảnh…
            </p>
          )}

          <div style={{ display: 'flex', gap: 10, justifyContent: 'center', marginTop: 16 }}>
            {!shotPreview && (
              <button className="btn btn-primary" onClick={capture} disabled={submitting}>
                <Camera size={16} weight="bold" /> Chụp
              </button>
            )}
            {shotPreview && !stepDone && (
              <button className="btn btn-ghost" onClick={retake} disabled={submitting}>Chụp lại</button>
            )}
            {stepDone && (
              <button className="btn btn-primary" onClick={nextStep}>
                {step < 3 ? 'Tiếp theo' : 'Hoàn tất'}
              </button>
            )}
          </div>
        </div>
      )}

      {step >= 4 && (
        <div className="card empty-state" style={{ maxWidth: 460, margin: '0 auto' }}>
          <CheckCircle size={40} weight="fill" color="var(--success)" />
          <p style={{ fontWeight: 700, fontSize: 15, color: 'var(--text)' }}>Đăng ký khuôn mặt hoàn tất</p>
          <p>Đã lưu thành công {successCount}/3 ảnh.</p>
          <span className="tag tag-warning">
            <HourglassMedium size={12} weight="bold" style={{ verticalAlign: -1 }} /> Chờ duyệt
          </span>
          <p style={{ marginTop: 8 }}>
            Quản trị viên sẽ duyệt trong thời gian sớm nhất. Bạn có thể dùng điểm danh bằng khuôn mặt
            sau khi dữ liệu được duyệt.
          </p>
        </div>
      )}
    </div>
  )
}

/** Giu nguyen luong cu cho admin/giang vien: tra cuu SV theo ID roi dang ky ho
 * (vd khi SV khong tu thao tac duoc). Khong dung stepper vi day la thao tac ho. */
function AdminLookupEnroll() {
  const webcamRef = useRef(null)
  const [studentId, setStudentId] = useState('')
  const [student, setStudent] = useState(null)
  const [lookupError, setLookupError] = useState('')
  const [shots, setShots] = useState([])
  const [message, setMessage] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [consenting, setConsenting] = useState(false)

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
      setLookupError('Không thể xác nhận đồng ý (cần sinh viên hoặc admin xác nhận).')
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
                {role === 'admin' && (
                  <button className="btn btn-primary" onClick={giveConsent} disabled={consenting}>
                    {consenting ? 'Đang xác nhận…' : 'Xác nhận đồng ý hộ'}
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
              Đã chụp {shots.length} ảnh
            </p>

            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <button className="btn btn-primary" onClick={capture} disabled={shots.length >= 5}>
                <Camera size={16} weight="bold" /> Chụp
              </button>
              <button className="btn btn-ghost" onClick={submit} disabled={!shots.length || submitting}>
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
            <p>Nhập Student ID và bấm "Tra cứu" để bắt đầu.</p>
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
                alt={`Ảnh khuôn mặt số ${i + 1}`}
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
