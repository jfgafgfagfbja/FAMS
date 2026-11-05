"""Noi dung dong y su dung du lieu sinh trac hoc (khuon mat).

Du lieu khuon mat la du lieu ca nhan nhay cam: chi duoc thu thap va xu ly khi chinh sinh
vien dong y ro rang, biet ro thu thap gi, de lam gi, giu bao lau, ai xem duoc va rut lai
the nao. Noi dung nam o may chu (khong viet cung trong app) va co PHIEN BAN: luc SV dong y,
he thong ghi lai SV da dong y voi phien ban nao. Doi noi dung thi tang CONSENT_VERSION - SV
da dong y phien ban cu se duoc app nhac doc va xac nhan lai.
"""
from app.core.config import settings

CONSENT_VERSION = "2026-10"

CONSENT_TITLE = "Đồng ý sử dụng dữ liệu khuôn mặt (sinh trắc học)"


def consent_items() -> list[str]:
    return [
        "Mục đích: dữ liệu khuôn mặt CHỈ dùng để điểm danh tại các buổi học của bạn, "
        "không dùng vào việc khác và không chia sẻ ra ngoài nhà trường.",
        "Dữ liệu thu thập: ảnh khuôn mặt lúc đăng ký (chỉ lưu tạm để cán bộ đối chiếu khi "
        "duyệt, xóa ngay sau khi duyệt) và một vector đặc trưng khuôn mặt dùng để nhận diện.",
        f"Mỗi lần điểm danh, hệ thống lưu một ảnh bằng chứng trong {settings.EVIDENCE_RETENTION_DAYS} "
        "ngày rồi tự động xóa.",
        "Người được xem: giảng viên lớp bạn học, Phòng Công tác sinh viên, lãnh đạo và văn "
        "phòng Khoa quản lý bạn — theo đúng phạm vi quyền của từng người.",
        "Thời gian lưu vector khuôn mặt: cho tới khi bạn rút đồng ý hoặc ra trường.",
        "Bạn có quyền RÚT ĐỒNG Ý bất kỳ lúc nào: toàn bộ ảnh và vector khuôn mặt của bạn bị "
        "xóa ngay.",
        "Không đồng ý hoặc rút đồng ý không ảnh hưởng quyền học tập: bạn vẫn được điểm danh "
        "bằng cách giảng viên xác nhận trực tiếp.",
        "Việc thu thập và xử lý tuân theo quy định của pháp luật Việt Nam về bảo vệ dữ liệu "
        "cá nhân; mọi thao tác đồng ý, rút đồng ý đều được ghi vào nhật ký hệ thống.",
    ]


CONSENT_CHECKBOX = ("Tôi đã đọc, hiểu rõ và tự nguyện đồng ý cho FAMS thu thập, xử lý dữ liệu "
                    "khuôn mặt của tôi theo đúng các nội dung trên.")

# Cach ghi nhan dong y.
METHOD_SELF = "self"    # chinh SV bam dong y trong app
METHOD_PAPER = "paper"  # SV ky ban giay, can bo P.CTSV/admin nhap thay (ghi ten nguoi nhap)
