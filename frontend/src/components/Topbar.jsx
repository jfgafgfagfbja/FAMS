import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { MagnifyingGlass, Sun, Moon } from '@phosphor-icons/react'

const ROLE_LABELS = {
  admin: 'Quản trị viên',
  lecturer: 'Giảng viên',
  student: 'Sinh viên',
}

/** Header toan trang: logo + tim kiem (chi admin, tra ve trang quan tri Sinh vien) + user. */
export default function Topbar({ theme, onToggleTheme }) {
  const navigate = useNavigate()
  const role = sessionStorage.getItem('role') || ''
  const email = sessionStorage.getItem('email') || ''
  const initials = email ? email.slice(0, 2).toUpperCase() : '?'
  const [query, setQuery] = useState('')
  const canSearch = role === 'admin'

  const submitSearch = (e) => {
    e.preventDefault()
    if (!query.trim()) return
    navigate(`/admin/students?q=${encodeURIComponent(query.trim())}`)
  }

  return (
    <header className="app-header">
      <Link to="/" className="app-logo">
        <span className="app-logo-mark">FA</span>
        FAMS
      </Link>

      {canSearch && (
        <form className="header-search-wrap" onSubmit={submitSearch}>
          <MagnifyingGlass size={16} className="header-search-icon" />
          <input
            type="search"
            placeholder="Tìm sinh viên theo tên hoặc MSSV…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </form>
      )}

      <div className="header-actions">
        <button className="icon-btn" onClick={onToggleTheme} aria-label="Đổi giao diện sáng/tối">
          {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
        </button>
        {email && (
          <div className="user-chip">
            <span className="user-avatar">{initials}</span>
            <span className="user-chip-text">
              <span className="user-chip-name">{email}</span>
              <span className="user-chip-role">{ROLE_LABELS[role] || role}</span>
            </span>
          </div>
        )}
      </div>
    </header>
  )
}
