export default function StatCard({ icon: Icon, label, value, tint = 'accent' }) {
  return (
    <div className="card stat-card">
      <div className="stat-card-top">
        <span
          className="stat-icon"
          style={{ background: `var(--${tint}-soft)`, color: `var(--${tint})` }}
        >
          <Icon size={18} weight="bold" />
        </span>
      </div>
      <div className="stat-value">{value}</div>
      <div className="stat-label">{label}</div>
    </div>
  )
}
