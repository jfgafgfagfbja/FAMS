import { useState } from 'react'

/** Hook quan ly state cho ToastStack: tra ve [toasts, pushToast] - toast tu
 * bien mat sau 4s. Dung kem <ToastStack toasts={toasts} />. */
export function useToasts() {
  const [toasts, setToasts] = useState([])
  const pushToast = (message) => {
    const id = `${Date.now()}-${Math.random()}`
    setToasts((prev) => [...prev, { id, message }])
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 4000)
  }
  return [toasts, pushToast]
}

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
