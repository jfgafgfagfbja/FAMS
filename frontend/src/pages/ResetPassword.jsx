import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import api from '../api'

/** Dat lai mat khau: nhap OTP (6 so) + mat khau moi (>= 8 ky tu, nhap lai de xac nhan). */
export default function ResetPassword() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const [email, setEmail] = useState(searchParams.get('email') || '')
  const [otp, setOtp] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)
  const [loading, setLoading] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setError('')

    if (newPassword.length < 8) {
      setError('Mật khẩu mới phải có ít nhất 8 ký tự.')
      return
    }
    if (newPassword !== confirmPassword) {
      setError('Mật khẩu nhập lại không khớp.')
      return
    }

    setLoading(true)
    try {
      await api.post('/auth/reset-password', { email, otp, new_password: newPassword })
      setSuccess(true)
    } catch (err) {
      setError(err.response?.data?.detail || 'Không đặt lại được mật khẩu. Vui lòng thử lại.')
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
            Đặt lại mật khẩu
          </p>
        </div>

        {success ? (
          <>
            <p style={{ fontSize: 13.5, margin: 0 }}>
              Đặt lại mật khẩu thành công. Các phiên đăng nhập cũ đã bị vô hiệu hóa.
            </p>
            <button type="button" className="btn btn-primary" onClick={() => navigate('/login')}>
              Đăng nhập ngay
            </button>
          </>
        ) : (
          <form onSubmit={submit} style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
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

            <div className="field">
              <label htmlFor="otp">Mã OTP</label>
              <input
                id="otp"
                required
                inputMode="numeric"
                maxLength={6}
                value={otp}
                onChange={(e) => setOtp(e.target.value.replace(/\D/g, ''))}
                placeholder="6 chữ số"
              />
            </div>

            <div className="field">
              <label htmlFor="newPassword">Mật khẩu mới</label>
              <input
                id="newPassword"
                type="password"
                required
                minLength={8}
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="Ít nhất 8 ký tự"
              />
            </div>

            <div className="field">
              <label htmlFor="confirmPassword">Nhập lại mật khẩu mới</label>
              <input
                id="confirmPassword"
                type="password"
                required
                minLength={8}
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Nhập lại mật khẩu mới"
              />
            </div>

            {error && <p className="field-error">{error}</p>}

            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? 'Đang xử lý…' : 'Đặt lại mật khẩu'}
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
