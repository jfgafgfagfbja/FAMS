import { Link } from 'react-router-dom'

export default function StatCard({ icon: Icon, label, value, tint = 'accent', to }) {
  return (
    <div className="card stat-card" style={{ background: `var(--${tint}-soft)` }}>
      <div className="stat-card-top">
        <span className="stat-label">{label}</span>
        {Icon && (
          <span className="stat-icon" style={{ color: `var(--${tint})` }}>
            <Icon size={16} weight="bold" />
          </span>
        )}
      </div>
      <div className="stat-value" style={{ color: `var(--${tint})` }}>{value}</div>
      {to && (
        <Link to={to} className="stat-link" style={{ color: `var(--${tint})` }}>
          Xem chi tiết →
        </Link>
      )}
    </div>
  )
}
