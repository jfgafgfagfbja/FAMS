import { CaretLeft, CaretRight } from '@phosphor-icons/react'

/** Thanh phan trang dung chung cho cac bang quan tri (Sinh vien/Giang vien/Lop/Lich hoc). */
export default function Pagination({ page, pageSize, total, onPageChange }) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize))
  if (totalPages <= 1) return null

  return (
    <div className="pagination">
      <button
        className="icon-btn"
        onClick={() => onPageChange(page - 1)}
        disabled={page <= 1}
        aria-label="Trang trước"
      >
        <CaretLeft size={14} />
      </button>
      <span className="pagination-info">Trang {page}/{totalPages} · {total} kết quả</span>
      <button
        className="icon-btn"
        onClick={() => onPageChange(page + 1)}
        disabled={page >= totalPages}
        aria-label="Trang sau"
      >
        <CaretRight size={14} />
      </button>
    </div>
  )
}
