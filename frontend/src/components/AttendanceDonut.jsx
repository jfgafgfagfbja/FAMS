const SIZE = 96
const STROKE = 10
const RADIUS = (SIZE - STROKE) / 2
const CIRCUMFERENCE = 2 * Math.PI * RADIUS

/** Vong tron tien do chuyen can 1 lop, kieu "18/20 buoi co mat" - SVG thuan, khong dung thu vien chart. */
export default function AttendanceDonut({ present, total, label }) {
  const ratio = total > 0 ? present / total : 0
  const offset = CIRCUMFERENCE * (1 - ratio)
  const color = ratio >= 0.8 ? 'var(--success)' : ratio >= 0.6 ? 'var(--warning)' : 'var(--danger)'

  return (
    <div className="donut-wrap" style={{ width: SIZE, height: SIZE }}>
      <svg width={SIZE} height={SIZE} viewBox={`0 0 ${SIZE} ${SIZE}`}>
        <circle
          cx={SIZE / 2} cy={SIZE / 2} r={RADIUS}
          fill="none" stroke="var(--border)" strokeWidth={STROKE}
        />
        <circle
          cx={SIZE / 2} cy={SIZE / 2} r={RADIUS}
          fill="none" stroke={color} strokeWidth={STROKE}
          strokeDasharray={CIRCUMFERENCE} strokeDashoffset={offset}
          strokeLinecap="round"
          transform={`rotate(-90 ${SIZE / 2} ${SIZE / 2})`}
        />
      </svg>
      <div className="donut-center">
        <span className="donut-value">{present}/{total}</span>
        {label && <span className="donut-caption">{label}</span>}
      </div>
    </div>
  )
}
