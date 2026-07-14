import { NavLink } from 'react-router-dom'
import { CaretLineLeft, SignOut } from '@phosphor-icons/react'
import { getNavItems } from '../nav'

export default function Sidebar({ collapsed, onToggleCollapse, onLogout }) {
  const navItems = getNavItems(sessionStorage.getItem('role'))

  return (
    <aside className={`sidebar${collapsed ? ' collapsed' : ''}`}>
      <button
        className="sidebar-collapse-btn"
        onClick={onToggleCollapse}
        aria-label={collapsed ? 'Mở rộng menu' : 'Thu gọn menu'}
      >
        <CaretLineLeft size={16} />
      </button>

      <nav className="sidebar-nav">
        {navItems.map(({ path, label, icon: Icon }) => (
          <NavLink
            key={path}
            to={path}
            end={path === '/'}
            title={collapsed ? label : undefined}
            className={({ isActive }) => `sidebar-link${isActive ? ' active' : ''}`}
          >
            <Icon size={18} weight="regular" />
            <span className="sidebar-link-label">{label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-footer">
        <button
          className="sidebar-link"
          style={{ width: '100%', border: 'none', background: 'none', cursor: 'pointer' }}
          onClick={onLogout}
          title={collapsed ? 'Đăng xuất' : undefined}
        >
          <SignOut size={18} />
          <span className="sidebar-link-label">Đăng xuất</span>
        </button>
      </div>
    </aside>
  )
}
