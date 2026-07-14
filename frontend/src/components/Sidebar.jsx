import { NavLink } from 'react-router-dom'
import { SignOut } from '@phosphor-icons/react'
import { getNavItems } from '../nav'

export default function Sidebar({ onLogout }) {
  const navItems = getNavItems(sessionStorage.getItem('role'))

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <span className="sidebar-logo-mark">FA</span>
        FAMS
      </div>

      <nav className="sidebar-nav">
        {navItems.map(({ path, label, icon: Icon }) => (
          <NavLink
            key={path}
            to={path}
            end={path === '/'}
            className={({ isActive }) => `sidebar-link${isActive ? ' active' : ''}`}
          >
            <Icon size={18} weight="regular" />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-footer">
        <button className="sidebar-link" style={{ width: '100%', border: 'none', background: 'none', cursor: 'pointer' }} onClick={onLogout}>
          <SignOut size={18} />
          Đăng xuất
        </button>
      </div>
    </aside>
  )
}
