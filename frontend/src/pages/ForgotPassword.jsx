import { useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../api'

/** Quen mat khau: nhap email -> gui OTP qua email. Luon hien thong bao chung
 * (khong tiet lo email co ton tai hay khong), khop voi backend. */
export default function ForgotPassword() {
  const [email, setEmail] = useState('')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [sent, setSent] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const { data } = await api.post('/auth/forgot-password', { email })
      setMessage(data.message)
      setSent(true)
    } catch (err) {
      if (err.response?.status === 429) {
        setError('Bạn đã yêu cầu quá nhiều lần. Vui lòng thử lại sau ít phút.')
      } else {
        setError('Không thể gửi yêu cầu lúc này. Vui lòng thử lại.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-shell">
      <div className="card auth-card">
        <div>
          <div className="app-logo" style={{ marginBottom: 4 }}>
            <span className="app-logo-mark">FA</span>
            FAMS
          </div>
          <p style={{ color: 'var(--text-muted)', fontSize: 13.5, margin: '4px 0 0' }}>
            Quên mật khẩu
          </p>
        </div>

        {sent ? (
          <>
            <p style={{ fontSize: 13.5, margin: 0 }}>{message}</p>
            <Link to={`/reset-password?email=${encodeURIComponent(email)}`} className="btn btn-primary">
              Tôi đã có mã OTP
            </Link>
          </>
        ) : (
          <form onSubmit={submit} style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
            <p style={{ fontSize: 13, color: 'var(--text-muted)', margin: 0 }}>
              Nhập email đã đăng ký, hệ thống sẽ gửi mã OTP gồm 6 số để đặt lại mật khẩu.
            </p>
            <div className="field">
              <label htmlFor="email">Email</label>
              <input
                id="email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="ten@fams.edu.vn"
              />
            </div>

            {error && <p className="field-error">{error}</p>}

            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? 'Đang gửi…' : 'Gửi mã OTP'}
            </button>
          </form>
        )}

        <Link to="/login" style={{ fontSize: 13, color: 'var(--accent)', textAlign: 'center' }}>
          Quay lại đăng nhập
        </Link>
      </div>
    </div>
  )
}
