import { useEffect, useState } from 'react'
import { Navigate, Route, Routes, useNavigate } from 'react-router-dom'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import LecturerDashboard from './pages/LecturerDashboard'
import StudentDashboard from './pages/StudentDashboard'
import MyAttendance from './pages/MyAttendance'
import AttendanceScreen from './pages/AttendanceScreen'
import SessionRecords from './pages/SessionRecords'
import EnrollFace from './pages/EnrollFace'
import Students from './pages/Students'
import Classes from './pages/Classes'
import ClassDetail from './pages/ClassDetail'
import Lecturers from './pages/Lecturers'
import AdminSchedules from './pages/AdminSchedules'
import Schedule from './pages/Schedule'
import SessionsList from './pages/SessionsList'
import LecturerReports from './pages/LecturerReports'
import FaceReview from './pages/FaceReview'
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

  const HomePage = role === 'student' ? StudentDashboard : role === 'lecturer' ? LecturerDashboard : Dashboard
  const isStaff = role === 'lecturer' || role === 'admin'

  return (
    <Layout theme={theme} onToggleTheme={toggleTheme} onLogout={logout}>
      <Routes>
        <Route path="/login" element={<Navigate to="/" />} />
        <Route path="/" element={<HomePage />} />
        <Route path="/schedule" element={<Schedule />} />
        <Route path="/enroll" element={<EnrollFace />} />

        <Route path="/my-attendance" element={role === 'student' ? <MyAttendance /> : <Navigate to="/" />} />

        <Route
          path="/attendance/:sessionId"
          element={isStaff ? <AttendanceScreen /> : <Navigate to="/" />}
        />
        <Route
          path="/sessions/:sessionId/records"
          element={isStaff ? <SessionRecords /> : <Navigate to="/" />}
        />
        <Route path="/sessions" element={role === 'lecturer' ? <SessionsList /> : <Navigate to="/" />} />
        <Route path="/reports" element={role === 'lecturer' ? <LecturerReports /> : <Navigate to="/" />} />

        <Route path="/admin/students" element={role === 'admin' ? <Students /> : <Navigate to="/" />} />
        <Route path="/admin/lecturers" element={role === 'admin' ? <Lecturers /> : <Navigate to="/" />} />
        <Route path="/admin/classes" element={role === 'admin' ? <Classes /> : <Navigate to="/" />} />
        <Route path="/admin/classes/:classId" element={role === 'admin' ? <ClassDetail /> : <Navigate to="/" />} />
        <Route path="/admin/schedules" element={role === 'admin' ? <AdminSchedules /> : <Navigate to="/" />} />
        <Route path="/face-review" element={role === 'admin' ? <FaceReview /> : <Navigate to="/" />} />

        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </Layout>
  )
}
