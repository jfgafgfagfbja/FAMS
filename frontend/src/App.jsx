import { lazy, Suspense, useEffect, useState } from 'react'
import { Navigate, Route, Routes, useNavigate } from 'react-router-dom'
import Login from './pages/Login'
import ForgotPassword from './pages/ForgotPassword'
import ResetPassword from './pages/ResetPassword'
import Layout from './components/Layout'
import { applyTheme, getActiveTheme } from './theme'
import api from './api'

// Cac trang duoi day duoc tach chunk rieng qua dynamic import (React.lazy) de
// SV/GV khong phai tai code chi danh cho admin (vd recharts trong Dashboard),
// va nguoc lai. Ket hop voi manualChunks trong vite.config.js de gop chung
// cac trang cung nhom (admin/attendance/enroll) vao it chunk hon.
const Dashboard = lazy(() => import('./pages/Dashboard'))
const LecturerDashboard = lazy(() => import('./pages/LecturerDashboard'))
const StudentDashboard = lazy(() => import('./pages/StudentDashboard'))
const MyAttendance = lazy(() => import('./pages/MyAttendance'))
const AttendanceScreen = lazy(() => import('./pages/AttendanceScreen'))
const SessionRecords = lazy(() => import('./pages/SessionRecords'))
const EnrollFace = lazy(() => import('./pages/EnrollFace'))
const Students = lazy(() => import('./pages/Students'))
const Classes = lazy(() => import('./pages/Classes'))
const ClassDetail = lazy(() => import('./pages/ClassDetail'))
const Lecturers = lazy(() => import('./pages/Lecturers'))
const AdminSchedules = lazy(() => import('./pages/AdminSchedules'))
const Schedule = lazy(() => import('./pages/Schedule'))
const SessionsList = lazy(() => import('./pages/SessionsList'))
const LecturerReports = lazy(() => import('./pages/LecturerReports'))
const FaceReview = lazy(() => import('./pages/FaceReview'))
const SelfCheckin = lazy(() => import('./pages/SelfCheckin'))
const Parents = lazy(() => import('./pages/Parents'))
const ParentChildren = lazy(() => import('./pages/ParentChildren'))
const ParentChildAttendance = lazy(() => import('./pages/ParentChildAttendance'))

function RouteFallback() {
  return <div className="route-fallback">Đang tải...</div>
}

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
        <Route path="/forgot-password" element={<ForgotPassword />} />
        <Route path="/reset-password" element={<ResetPassword />} />
        <Route path="*" element={<Navigate to="/login" />} />
      </Routes>
    )
  }

  const HomePage = role === 'student' ? StudentDashboard
    : role === 'lecturer' ? LecturerDashboard
    : role === 'parent' ? ParentChildren
    : Dashboard
  const isStaff = role === 'lecturer' || role === 'admin'

  return (
    <Layout theme={theme} onToggleTheme={toggleTheme} onLogout={logout}>
      <Suspense fallback={<RouteFallback />}>
        <Routes>
          <Route path="/login" element={<Navigate to="/" />} />
          <Route path="/" element={<HomePage />} />
          <Route path="/schedule" element={<Schedule />} />
          <Route path="/enroll" element={<EnrollFace />} />

          <Route path="/my-attendance" element={role === 'student' ? <MyAttendance /> : <Navigate to="/" />} />
          <Route path="/self-checkin/:sessionId" element={role === 'student' ? <SelfCheckin /> : <Navigate to="/" />} />

          <Route path="/parent/children/:studentId/attendance" element={role === 'parent' ? <ParentChildAttendance /> : <Navigate to="/" />} />

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
          <Route path="/admin/parents" element={role === 'admin' ? <Parents /> : <Navigate to="/" />} />

          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </Suspense>
    </Layout>
  )
}
