import { X } from '@phosphor-icons/react'

/** Modal dung chung cho cac form them/sua trong trang quan tri. */
export default function Modal({ title, onClose, children, width = 480 }) {
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="card modal-card" style={{ maxWidth: width }} onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3 style={{ margin: 0, fontSize: 16 }}>{title}</h3>
          <button className="icon-btn" onClick={onClose} aria-label="Đóng">
            <X size={16} />
          </button>
        </div>
        {children}
      </div>
    </div>
  )
}
