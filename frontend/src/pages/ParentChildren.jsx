import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { UsersThree, WarningCircle } from '@phosphor-icons/react'
import api from '../api'

/** Trang chu cua phu huynh: danh sach con em da duoc admin lien ket thu cong.
 * Bam vao 1 con de xem chi tiet chuyen can (anh/gio/vi tri diem danh). */
export default function ParentChildren() {
  const navigate = useNavigate()
  const [children, setChildren] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.get('/parents/me/children')
      .then(({ data }) => setChildren(data))
      .catch((err) => setError(err.response?.data?.detail || 'Không tải được danh sách con em.'))
  }, [])

  if (error) {
    return (
      <div className="card empty-state">
        <WarningCircle size={32} />
        <p>{error}</p>
      </div>
    )
  }

  if (children === null) {
    return <div className="card skeleton" style={{ height: 220 }} />
  }

  if (!children.length) {
    return (
      <div className="card empty-state">
        <UsersThree size={32} />
        <p>Bạn chưa được liên kết với sinh viên nào. Liên hệ quản trị viên nhà trường để được liên kết.</p>
      </div>
    )
  }

  return (
    <div className="card" style={{ padding: 20 }}>
      <h3 style={{ marginTop: 0, fontSize: 15 }}>Con em của tôi</h3>
      <div>
        {children.map((c) => (
          <div
            key={c.id}
            className="class-list-row"
            style={{ cursor: 'pointer' }}
            onClick={() => navigate(`/parent/children/${c.id}/attendance`)}
          >
            <div>
              <div className="class-list-code">{c.full_name}</div>
              <div className="class-list-subject">
                MSSV {c.student_code}{c.major ? ` · ${c.major}` : ''}{c.classes.length ? ` · ${c.classes.length} lớp học phần` : ''}
              </div>
            </div>
            <span className={`tag ${c.face_enrolled ? 'tag-success' : 'tag-neutral'}`}>
              {c.face_enrolled ? 'Đã đăng ký khuôn mặt' : 'Chưa đăng ký khuôn mặt'}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
