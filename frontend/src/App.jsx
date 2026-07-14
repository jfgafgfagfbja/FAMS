import { useEffect, useState } from 'react'
import { Navigate, Route, Routes, useNavigate } from 'react-router-dom'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import MyAttendance from './pages/MyAttendance'
import AttendanceScreen from './pages/AttendanceScreen'
import EnrollFace from './pages/EnrollFace'
import Students from './pages/Students'
import Classes from './pages/Classes'
import Layout from './components/Layout'
import { applyTheme, getActiveTheme } from './theme'
import api from './api'

export default function App() {
  const token = sessionStorage.getItem('token')
  const role = sessionStorage.getItem('role')
  const navigate = useNavigate()
  const [theme, setTheme] = useState(getActiveTheme)

  useEffect(() => {
    applyTheme(theme)
  }, [theme])

  const toggleTheme = () => setTheme((t) => (t === 'dark' ? 'light' : 'dark'))

  const logout = async () => {
    try {
      await api.post('/auth/logout')
    } catch {
      /* token da het han hoac mang loi - van tiep tuc xoa phien cuc bo */
    }
    sessionStorage.clear()
    navigate('/login')
  }

  if (!token) {
    return (
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="*" element={<Navigate to="/login" />} />
      </Routes>
    )
  }

  return (
    <Layout theme={theme} onToggleTheme={toggleTheme} onLogout={logout}>
      <Routes>
        <Route path="/login" element={<Navigate to="/" />} />
        <Route path="/" element={role === 'student' ? <MyAttendance /> : <Dashboard />} />
        <Route
          path="/attendance"
          element={role === 'student' ? <Navigate to="/" /> : <AttendanceScreen />}
        />
        <Route path="/enroll" element={<EnrollFace />} />
        <Route path="/students" element={role === 'admin' ? <Students /> : <Navigate to="/" />} />
        <Route path="/classes" element={role === 'admin' ? <Classes /> : <Navigate to="/" />} />
        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </Layout>
  )
}
