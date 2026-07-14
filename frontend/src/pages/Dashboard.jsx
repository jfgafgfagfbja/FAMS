import { useEffect, useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { CalendarCheck, GraduationCap, Users, WarningCircle } from '@phosphor-icons/react'
import api from '../api'
import StatCard from '../components/StatCard'

const CHART_COLORS = { present: '#22c55e', late: '#f59e0b', absent: '#ef4444' }

/** Dashboard: KPI tong quan + bieu do chuyen can theo lop + bang chi tiet. */
export default function Dashboard() {
  const [classes, setClasses] = useState([])
  const [studentCount, setStudentCount] = useState(null)
  const [reportsByClass, setReportsByClass] = useState({})
  const [selectedId, setSelectedId] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false

    async function load() {
      const { data: classList } = await api.get('/classes')
      if (cancelled) return
      setClasses(classList)
      if (classList.length) setSelectedId(classList[0].id)

      try {
        const { data: students } = await api.get('/students')
        if (!cancelled) setStudentCount(students.length)
      } catch {
        if (!cancelled) setStudentCount(null)
      }

      const entries = await Promise.all(
        classList.map(async (c) => {
          try {
            const { data } = await api.get(`/reports/attendance/${c.id}`)
            return [c.id, data]
          } catch {
            return [c.id, []]
          }
        }),
      )
      if (!cancelled) {
        setReportsByClass(Object.fromEntries(entries))
        setLoading(false)
      }
    }

    load()
    return () => {
      cancelled = true
    }
  }, [])

  if (loading) {
    return (
      <div>
        <div className="stat-grid">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="card stat-card skeleton" style={{ height: 112 }} />
          ))}
        </div>
        <div className="card skeleton" style={{ height: 320 }} />
      </div>
    )
  }

  if (!classes.length) {
    return (
      <div className="card empty-state">
        <GraduationCap size={32} />
        <p>Chưa có lớp học phần nào. Liên hệ quản trị viên để tạo lớp.</p>
      </div>
    )
  }

  const allReports = Object.values(reportsByClass).flat()
  const totalSessions = classes.reduce((sum, c) => sum + (reportsByClass[c.id]?.[0]?.total_sessions || 0), 0)
  const warningCount = allReports.filter((r) => r.warning).length
  const selectedClass = classes.find((c) => c.id === selectedId)
  const selectedReport = reportsByClass[selectedId] || []
  const chartData = selectedReport.map((r) => ({
    name: r.student_code,
    'Có mặt': r.present + r.manual,
    Muộn: r.late,
    Vắng: r.absent,
  }))

  return (
    <div>
      <div className="stat-grid">
        <StatCard icon={Users} label="Tổng sinh viên" value={studentCount ?? '—'} tint="accent" />
        <StatCard icon={GraduationCap} label="Lớp học phần" value={classes.length} tint="accent" />
        <StatCard icon={CalendarCheck} label="Buổi đã điểm danh" value={totalSessions} tint="success" />
        <StatCard icon={WarningCircle} label="Cảnh báo chuyên cần" value={warningCount} tint="warning" />
      </div>

      <div className="card" style={{ padding: 20, marginBottom: 20 }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginBottom: 16,
            flexWrap: 'wrap',
            gap: 12,
          }}
        >
          <div>
            <h3 style={{ margin: 0, fontSize: 15 }}>Chuyên cần theo lớp</h3>
            <p style={{ margin: '2px 0 0', color: 'var(--text-muted)', fontSize: 13 }}>
              {selectedClass?.subject_name} — {selectedClass?.class_code}
            </p>
          </div>
          <select
            className="select"
            value={selectedId ?? ''}
            onChange={(e) => setSelectedId(Number(e.target.value))}
          >
            {classes.map((c) => (
              <option key={c.id} value={c.id}>
                {c.class_code} — {c.subject_name}
              </option>
            ))}
          </select>
        </div>

        {chartData.length ? (
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
              <XAxis
                dataKey="name"
                tick={{ fontSize: 12, fill: 'var(--text-muted)' }}
                axisLine={{ stroke: 'var(--border)' }}
                tickLine={false}
              />
              <YAxis
                allowDecimals={false}
                tick={{ fontSize: 12, fill: 'var(--text-muted)' }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip
                contentStyle={{
                  background: 'var(--surface)',
                  border: '1px solid var(--border)',
                  borderRadius: 8,
                  fontSize: 13,
                }}
              />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Bar dataKey="Có mặt" stackId="a" fill={CHART_COLORS.present} />
              <Bar dataKey="Muộn" stackId="a" fill={CHART_COLORS.late} />
              <Bar dataKey="Vắng" stackId="a" fill={CHART_COLORS.absent} radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <div className="empty-state">
            <p>Lớp này chưa có buổi điểm danh nào được đóng.</p>
          </div>
        )}
      </div>

      <div className="card">
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>MSSV</th>
                <th>Họ tên</th>
                <th>Có mặt</th>
                <th>Muộn</th>
                <th>Vắng</th>
                <th>Tổng buổi</th>
                <th>Trạng thái</th>
              </tr>
            </thead>
            <tbody>
              {selectedReport.map((r) => (
                <tr key={r.student_code}>
                  <td>{r.student_code}</td>
                  <td>{r.full_name}</td>
                  <td>{r.present + r.manual}</td>
                  <td>{r.late}</td>
                  <td>{r.absent}</td>
                  <td>{r.total_sessions}</td>
                  <td>
                    {r.warning ? (
                      <span className="tag tag-warning">Nguy cơ cấm thi</span>
                    ) : (
                      <span className="tag tag-success">Bình thường</span>
                    )}
                  </td>
                </tr>
              ))}
              {!selectedReport.length && (
                <tr>
                  <td colSpan={7} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 24 }}>
                    Chưa có dữ liệu
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
