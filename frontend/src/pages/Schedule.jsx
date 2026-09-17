import { Fragment, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { CalendarBlank, Camera, CaretLeft, CaretRight, Printer } from '@phosphor-icons/react'
import api from '../api'
import ToastStack, { useToasts } from '../components/ToastStack'
import { WEEKDAYS, addDays, formatDDMMYYYY, hhmm, isWithinOpenWindow, toISODate, toMonday } from '../utils/format'

const role = sessionStorage.getItem('role')
const canOpenSession = role === 'lecturer'
const isStaffView = role === 'lecturer' || role === 'admin'

const CA_ROWS = [
  { key: 'morning', label: 'Sáng' },
  { key: 'afternoon', label: 'Chiều' },
  { key: 'evening', label: 'Tối' },
]

function classifyCa(startTime) {
  const hour = Number(startTime.split(':')[0])
  if (hour < 12) return 'morning'
  if (hour < 18) return 'afternoon'
  return 'evening'
}

const SV_STATUS_BADGE = {
  present: { label: '✓ Có mặt', tint: 'success' },
  manual: { label: '✓ Có mặt', tint: 'success' },
  late: { label: 'M Muộn', tint: 'warning' },
  absent: { label: '✗ Vắng', tint: 'danger' },
  excused: { label: 'Có phép', tint: 'neutral' },
}

/** Thoi khoa bieu tuan kieu DAU: Sang/Chieu/Toi x Thu 2..CN, gop trang thai phien/
 * diem danh tu GET /schedules/week. SV: badge ket qua diem danh cua chinh minh.
 * GV: mo phien / badge "dang diem danh" / "x/N co mat". Admin: xem toan bo, chi doc. */
export default function Schedule() {
  const navigate = useNavigate()
  const [weekStart, setWeekStart] = useState(() => toMonday(new Date()))
  const [slots, setSlots] = useState(null)
  const [opening, setOpening] = useState(null)
  const [toasts, pushToast] = useToasts()
  // Tick moi 30s de nut "Mo phien" tu hien/an khi buoc vao/ra khoi khung gio hop le
  const [now, setNow] = useState(() => new Date())

  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 30_000)
    return () => clearInterval(id)
  }, [])

  useEffect(() => {
    let cancelled = false
    setSlots(null)
    api.get('/schedules/week', { params: { start: toISODate(weekStart) } }).then(({ data }) => {
      if (!cancelled) setSlots(data)
    })
    return () => {
      cancelled = true
    }
  }, [weekStart])

  const openSession = async (scheduleId) => {
    setOpening(scheduleId)
    try {
      const { data } = await api.post('/sessions', {
        schedule_id: scheduleId, session_date: toISODate(new Date()),
      })
      navigate(`/attendance/${data.id}`)
    } catch (err) {
      pushToast(err.response?.data?.detail || 'Không mở được phiên điểm danh')
    } finally {
      setOpening(null)
    }
  }

  const days = Array.from({ length: 7 }, (_, i) => addDays(weekStart, i))
  const todayISO = toISODate(new Date())

  const slotsByDay = days.map((day) => {
    const iso = toISODate(day)
    const daySlots = (slots || []).filter((s) => s.date === iso)
    return CA_ROWS.map((ca) => daySlots.filter((s) => classifyCa(s.start_time) === ca.key))
  })

  return (
    <div>
      <ToastStack toasts={toasts} />

      <div className="week-nav">
        <span className="week-nav-range">
          {formatDDMMYYYY(days[0])} – {formatDDMMYYYY(days[6])}
        </span>
        <div className="week-nav-actions no-print">
          <button className="btn btn-ghost" onClick={() => setWeekStart((d) => addDays(d, -7))}>
            <CaretLeft size={14} /> Trở về
          </button>
          <button className="btn btn-ghost" onClick={() => setWeekStart(toMonday(new Date()))}>
            Hiện tại
          </button>
          <button className="btn btn-ghost" onClick={() => setWeekStart((d) => addDays(d, 7))}>
            Tiếp <CaretRight size={14} />
          </button>
          <button className="btn btn-ghost" onClick={() => window.print()}>
            <Printer size={16} /> In lịch
          </button>
        </div>
      </div>

      {slots === null ? (
        <div className="card skeleton" style={{ height: 320 }} />
      ) : !slots.length ? (
        <div className="card empty-state">
          <CalendarBlank size={32} />
          <p>
            {role === 'student'
              ? 'Bạn chưa ghi danh lớp học phần nào nên chưa có lịch học.'
              : role === 'lecturer'
                ? 'Bạn chưa được phân công lớp học phần nào nên chưa có lịch dạy.'
                : 'Chưa có lịch học nào được tạo.'}
          </p>
        </div>
      ) : (
        <div className="card" style={{ padding: 20 }}>
          <div className="timetable-wrap">
            <div className="timetable-grid">
              <div />
              {days.map((day) => {
                const iso = toISODate(day)
                return (
                  <div key={iso} className={`timetable-head${iso === todayISO ? ' today' : ''}`}>
                    <span className="timetable-head-day">{WEEKDAYS[(day.getDay() + 6) % 7]}</span>
                    <span className="timetable-head-date">{formatDDMMYYYY(day)}</span>
                  </div>
                )
              })}

              {CA_ROWS.map((ca, caIdx) => (
                <Fragment key={ca.key}>
                  <div className="timetable-row-label">{ca.label}</div>
                  {days.map((day, dayIdx) => {
                    const iso = toISODate(day)
                    const cellSlots = slotsByDay[dayIdx][caIdx]
                    return (
                      <div key={`${ca.key}-${iso}`} className={`timetable-cell${iso === todayISO ? ' today' : ''}`}>
                        {cellSlots.map((s) => (
                          <ScheduleSlot
                            key={s.schedule_id + s.date}
                            slot={s}
                            isToday={iso === todayISO}
                            isPast={iso < todayISO}
                            now={now}
                            opening={opening === s.schedule_id}
                            onOpenSession={() => openSession(s.schedule_id)}
                          />
                        ))}
                      </div>
                    )
                  })}
                </Fragment>
              ))}
            </div>
          </div>

          <div className="schedule-legend no-print">
            <span><span className="legend-dot" style={{ background: 'var(--success)' }} /> Có mặt / Đang điểm danh</span>
            <span><span className="legend-dot" style={{ background: 'var(--warning)' }} /> Muộn</span>
            <span><span className="legend-dot" style={{ background: 'var(--danger)' }} /> Vắng</span>
            <span><span className="legend-dot" style={{ background: 'var(--neutral-soft)', border: '1px solid var(--border)' }} /> Chưa điểm danh / đã đóng</span>
          </div>
        </div>
      )}
    </div>
  )
}

function ScheduleSlot({ slot, isToday, isPast, now, opening, onOpenSession }) {
  const timeLabel = `${slot.start_time.slice(0, 5)}–${slot.end_time.slice(0, 5)}`
  const body = (
    <>
      <strong>{slot.class_code}</strong>
      <span>{slot.subject_name}</span>
      <span>{timeLabel} · P.{slot.room}</span>
    </>
  )

  if (role === 'student') {
    const badge = (isPast || isToday) ? SV_STATUS_BADGE[slot.my_status] : null
    // Chi cho tu diem danh khi phien dang mo HOM NAY va chinh SV chua co ket qua nao.
    const canSelfCheckin = isToday && slot.session_status === 'open' && !slot.my_status
    return (
      <div className="timetable-slot">
        {body}
        {badge && <span className={`timetable-slot-badge tag-${badge.tint}`}>{badge.label}</span>}
        {canSelfCheckin && (
          <Link
            to={`/self-checkin/${slot.session_id}`}
            state={{ classCode: slot.class_code, subjectName: slot.subject_name, room: slot.room }}
            className="btn btn-primary no-print"
            style={{ padding: '4px 8px', fontSize: 11, alignSelf: 'flex-start', textDecoration: 'none' }}
          >
            <Camera size={13} weight="bold" /> Tự điểm danh
          </Link>
        )}
      </div>
    )
  }

  if (isStaffView) {
    if (slot.session_status === 'open') {
      return (
        <Link to={`/attendance/${slot.session_id}`} className="timetable-slot" style={{ textDecoration: 'none', color: 'inherit' }}>
          {body}
          <span className="timetable-slot-badge tag-success tag-blink">● Đang điểm danh</span>
        </Link>
      )
    }
    if (slot.session_status === 'closed') {
      return (
        <Link to={`/sessions/${slot.session_id}/records`} className="timetable-slot" style={{ textDecoration: 'none', color: 'inherit' }}>
          {body}
          <span className="timetable-slot-badge tag-neutral">{slot.present_count}/{slot.total_count} có mặt</span>
        </Link>
      )
    }
    const withinWindow = isWithinOpenWindow(slot.open_from, slot.end_time, now)
    const beforeWindow = now.toTimeString().slice(0, 8) < (slot.open_from || '')
    return (
      <div className="timetable-slot">
        {body}
        {isToday && canOpenSession && withinWindow && (
          <button
            className="btn btn-primary no-print"
            style={{ padding: '4px 8px', fontSize: 11, alignSelf: 'flex-start' }}
            onClick={onOpenSession}
            disabled={opening}
          >
            {opening ? 'Đang mở…' : 'Mở phiên'}
          </button>
        )}
        {isToday && canOpenSession && beforeWindow && (
          <span
            className="timetable-slot-badge tag-neutral no-print"
            title={`Chỉ mở được từ ${hhmm(slot.open_from)}`}
          >
            Mở từ {hhmm(slot.open_from)}
          </span>
        )}
      </div>
    )
  }

  return <div className="timetable-slot">{body}</div>
}
