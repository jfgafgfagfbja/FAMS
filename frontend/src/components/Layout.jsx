import { useState } from 'react'
import { useLocation } from 'react-router-dom'
import Sidebar from './Sidebar'
import Topbar from './Topbar'
import { getNavItems } from '../nav'

const EXTRA_TITLES = [
  { prefix: '/attendance/', label: 'Điểm danh' },
  { prefix: '/sessions/', label: 'Kết quả điểm danh' },
]

const SIDEBAR_COLLAPSED_KEY = 'fams-sidebar-collapsed'

export default function Layout({ theme, onToggleTheme, onLogout, children }) {
  const location = useLocation()
  const [collapsed, setCollapsed] = useState(() => localStorage.getItem(SIDEBAR_COLLAPSED_KEY) === '1')

  const toggleCollapsed = () => {
    setCollapsed((c) => {
      const next = !c
      localStorage.setItem(SIDEBAR_COLLAPSED_KEY, next ? '1' : '0')
      return next
    })
  }

  const role = sessionStorage.getItem('role') || ''
  const navItems = getNavItems(role)
  const current = navItems.find((item) =>
    item.path === '/' ? location.pathname === '/' : location.pathname.startsWith(item.path),
  )
  const extra = EXTRA_TITLES.find((t) => location.pathname.startsWith(t.prefix))
  const title = current?.label || extra?.label || 'FAMS'

  return (
    <div className="app-shell">
      <Topbar theme={theme} onToggleTheme={onToggleTheme} />
      <div className="body-row">
        <Sidebar collapsed={collapsed} onToggleCollapse={toggleCollapsed} onLogout={onLogout} />
        <main className="page">
          <h1 className="page-title">{title}</h1>
          {children}
        </main>
      </div>
    </div>
  )
}
