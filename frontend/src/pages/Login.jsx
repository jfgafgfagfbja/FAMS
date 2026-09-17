import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import api from '../api'

export default function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const form = new URLSearchParams({ username: email, password })
      const { data } = await api.post('/auth/login', form)
      sessionStorage.setItem('token', data.access_token)
      sessionStorage.setItem('role', data.role)
      sessionStorage.setItem('email', email)
      navigate('/')
      window.location.reload()
    } catch (err) {
      if (err.response?.status === 429) {
        setError('Bạn đã đăng nhập sai quá nhiều lần. Vui lòng thử lại sau ít phút.')
      } else if (err.response?.status === 401) {
        setError('Sai email hoặc mật khẩu.')
      } else {
        setError('Không thể đăng nhập lúc này. Vui lòng thử lại.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-shell">
      <form onSubmit={submit} className="card auth-card">
        <div>
          <div className="app-logo" style={{ marginBottom: 4 }}>
            <span className="app-logo-mark">FA</span>
            FAMS
          </div>
          <p style={{ color: 'var(--text-muted)', fontSize: 13.5, margin: '4px 0 0' }}>
            Trường Đại học Kiến trúc Đà Nẵng — Hệ thống điểm danh bằng khuôn mặt
          </p>
        </div>

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
          <label htmlFor="password">Mật khẩu</label>
          <input
            id="password"
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
          />
        </div>

        {error && <p className="field-error">{error}</p>}

        <button type="submit" className="btn btn-primary" disabled={loading}>
          {loading ? 'Đang đăng nhập…' : 'Đăng nhập'}
        </button>

        <Link to="/forgot-password" style={{ fontSize: 13, color: 'var(--accent)', textAlign: 'center' }}>
          Quên mật khẩu?
        </Link>
      </form>
    </div>
  )
}
