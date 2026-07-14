/** Ngan xep toast goc phai man hinh, tu bien mat sau vai giay (quan ly boi cha qua hook). */
export default function ToastStack({ toasts }) {
  if (!toasts.length) return null
  return (
    <div className="toast-stack">
      {toasts.map((t) => (
        <div key={t.id} className="toast">{t.message}</div>
      ))}
    </div>
  )
}
