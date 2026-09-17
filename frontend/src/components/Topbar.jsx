import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { MagnifyingGlass, Sun, Moon, Bell } from '@phosphor-icons/react'
import api from '../api'

const ROLE_LABELS = {
  admin: 'Quản trị viên',
  lecturer: 'Giảng viên',
  student: 'Sinh viên',
  parent: 'Phụ huynh',
}

// Trang dich khi bam chuong thong bao, tuy vai tro - noi co the xu ly canh bao tuong ung.
const BELL_TARGET = {
  admin: '/face-review',
  lecturer: '/reports',
  student: '/my-attendance',
}

/** So luong "canh bao" can chu y, lay tu du lieu that cua FAMS (khong phai thong bao gia):
 * admin -> so khuon mat cho duyet; giang vien -> so SV vuot nguong vang trong cac lop minh day;
 * sinh vien -> so lop chinh minh dang vuot nguong vang. */
function useAlertCount(role) {
  const [count, setCount] = useState(0)

  useEffect(() => {
    let cancelled = false

    async function load() {
      try {
        if (role === 'admin') {
          const { data } = await api.get('/faces/pending')
          if (!cancelled) setCount(data.length)
        } else if (role === 'lecturer') {
          const { data: me } = await api.get('/auth/me')
          const lists = await Promise.all(
            (me.classes || []).map(async (c) => {
              try {
                const { data } = await api.get('/reports/attendance/warnings', { params: { class_id: c.id } })
                return data.map((r) => r.student_id)
              } catch {
                return []
              }
            }),
          )
          if (!cancelled) setCount(new Set(lists.flat()).size)
        } else if (role === 'student') {
          const { data } = await api.get('/reports/my-attendance')
          if (!cancelled) setCount(data.filter((r) => r.warning).length)
        }
      } catch {
        if (!cancelled) setCount(0)
      }
    }

    if (role) load()
    return () => {
      cancelled = true
    }
  }, [role])

  return count
}

/** Header toan trang: logo + tim kiem (chi admin, tra ve trang quan tri Sinh vien) + chuong canh
 * bao chuyen can/duyet khuon mat (theo vai tro) + user. */
export default function Topbar({ theme, onToggleTheme }) {
  const navigate = useNavigate()
  const role = sessionStorage.getItem('role') || ''
  const email = sessionStorage.getItem('email') || ''
  const initials = email ? email.slice(0, 2).toUpperCase() : '?'
  const [query, setQuery] = useState('')
  const canSearch = role === 'admin'
  const alertCount = useAlertCount(role)

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
        {BELL_TARGET[role] && (
          <button
            className="icon-btn icon-btn-bell"
            onClick={() => navigate(BELL_TARGET[role])}
            aria-label="Cảnh báo chuyên cần"
            title={alertCount > 0 ? `${alertCount} mục cần chú ý` : 'Không có cảnh báo mới'}
          >
            <Bell size={18} />
            {alertCount > 0 && (
              <span className="icon-btn-badge">{alertCount > 99 ? '99+' : alertCount}</span>
            )}
          </button>
        )}
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
