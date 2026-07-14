import Sidebar from './Sidebar'
import Topbar from './Topbar'

export default function Layout({ theme, onToggleTheme, onLogout, children }) {
  return (
    <div className="app-shell">
      <Sidebar onLogout={onLogout} />
      <div className="main-col">
        <Topbar theme={theme} onToggleTheme={onToggleTheme} />
        <div className="page">{children}</div>
      </div>
    </div>
  )
}
