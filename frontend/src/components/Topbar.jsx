import { useLocation } from 'react-router-dom'
import { Sun, Moon } from '@phosphor-icons/react'
import { getNavItems } from '../nav'

const ROLE_LABELS = {
  admin: 'Quản trị viên',
  lecturer: 'Giảng viên',
  student: 'Sinh viên',
}

export default function Topbar({ theme, onToggleTheme }) {
  const location = useLocation()
  const role = sessionStorage.getItem('role') || ''
  const navItems = getNavItems(role)
  const current = navItems.find((item) =>
    item.path === '/' ? location.pathname === '/' : location.pathname.startsWith(item.path),
  )
  const email = sessionStorage.getItem('email') || ''
  const initials = email ? email.slice(0, 2).toUpperCase() : '?'

  return (
    <header className="topbar">
      <div className="topbar-title">{current?.label || 'FAMS'}</div>
      <div className="topbar-actions">
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
