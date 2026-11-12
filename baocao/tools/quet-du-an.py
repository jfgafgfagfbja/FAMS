"""Quet kho ma nguon FAMS -> sinh so lieu cho quyen bao cao va bo slide.

Chay:
    python baocao/tools/quet-du-an.py              # sinh lai file trong baocao/auto/
    python baocao/tools/quet-du-an.py --kiem-tra   # khong ghi, bao lech (dung cho CI)

Sinh ra (KHONG sua tay cac file nay):
    auto/du-lieu-du-an.tex     macro so lieu (\\FsoEndpoint, \\FnguongNhanDien...)
    auto/bang-api.tex          bang module API
    auto/bang-cau-hinh.tex     bang tham so cau hinh
    auto/bang-bang-du-lieu.tex bang luoc do CSDL
    auto/bang-test.tex         bang nhom kiem thu tu dong
    auto/hien-trang.json       anh chup hien trang lan quet truoc (de so lech)
    auto/thay-doi.md           nhung gi doi so voi lan quet truoc -> phan van xuoi can sua

MO TA tieng Viet cua tung module/tham so/bang nam trong 3 tu dien ben duoi. Khi du an
them module/tham so/bang moi ma chua co mo ta, script van sinh bang day du nhung danh
dau "(chua mo ta)" va liet ke trong thay-doi.md de nguoi viet bo sung.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

BAOCAO_DIR = Path(__file__).resolve().parents[1]
ROOT = BAOCAO_DIR.parent
AUTO_DIR = BAOCAO_DIR / "auto"

# ---------------------------------------------------------------------------
#  Mo ta tieng Viet - bo sung khi du an co module/tham so/bang moi
# ---------------------------------------------------------------------------
MO_TA_MODULE = {
    "auth": "Đăng nhập, làm mới token, đổi và quên mật khẩu, thông tin tài khoản",
    "students": "Hồ sơ sinh viên, đồng ý sinh trắc học có phiên bản và rút đồng ý, chuyên cần cá nhân",
    "lecturers": "Hồ sơ giảng viên, lịch dạy trong ngày",
    "classes": "Lớp học phần, ghi danh, lịch học của lớp",
    "schedules": "Tra cứu lịch học và thời khoá biểu theo tuần",
    "sessions": "Phiên điểm danh: mở, quét camera, mã QR xoay vòng, tự điểm danh, xác nhận tay, đóng phiên",
    "faces": "Đăng ký khuôn mặt, duyệt hoặc từ chối, dữ liệu khuôn mặt của sinh viên",
    "reports": "Báo cáo chuyên cần, cảnh báo vắng, xuất Excel, thống kê tổng hợp",
    "parents": "Tài khoản phụ huynh, liên kết với sinh viên, tuỳ chọn nhận thông báo",
    "units": "Đơn vị trong trường: Khoa, Phòng Đào tạo, Phòng CTSV, Ban ngành",
    "staff": "Tài khoản cán bộ phòng ban, gồm Văn phòng Khoa và Lãnh đạo Khoa",
    "locations": "Địa điểm điểm danh và bán kính cho phép khi tự điểm danh bằng GPS",
    "media": "Phát ảnh bằng chứng qua đường dẫn được ký điện tử (HMAC), có hạn dùng",
    "rooms": "Danh mục phòng học: toà nhà, tầng, sức chứa, toạ độ riêng của phòng",
    "notifications": "Hộp thư thông báo điểm danh của phụ huynh",
    "audit_logs": "Nhật ký hệ thống: ai thao tác gì, lúc nào, thay đổi những gì",
}

MO_TA_CAU_HINH = {
    "RECOGNITION_THRESHOLD": "Ngưỡng cosine để coi là khớp danh tính",
    "DUPLICATE_THRESHOLD": "Ngưỡng cảnh báo khuôn mặt trùng người khác khi đăng ký",
    "CONFIRM_FRAMES": "Số khung hình phải nhận diện đúng trước khi ghi điểm danh",
    "ANTISPOOF_ENABLED": "Bật hoặc tắt kiểm tra chống giả mạo",
    "ANTISPOOF_THRESHOLD": "Điểm “mặt thật” tối thiểu của MiniFASNetV2",
    "LATE_AFTER_MINUTES": "Sau bao nhiêu phút thì tính là đi muộn",
    "EARLY_OPEN_MINUTES": "Được mở phiên sớm trước giờ vào tiết",
    "SESSION_GRACE_MINUTES": "Sau giờ kết thúc bao lâu thì ngừng nhận và tự động đóng phiên",
    "EVIDENCE_RETENTION_DAYS": "Số ngày lưu ảnh bằng chứng trước khi xoá tự động",
    "MEDIA_URL_EXPIRE_MINUTES": "Thời hạn của đường dẫn ảnh được ký điện tử (HMAC)",
    "ACCESS_TOKEN_EXPIRE_MINUTES": "Thời hạn access token",
    "REFRESH_TOKEN_EXPIRE_DAYS": "Thời hạn refresh token của app mobile",
    "ABSENCE_WARN_RATIO": "Tỉ lệ vắng không phép chạm ngưỡng cảnh báo cấm thi",
    "SELF_CHECKIN_REQUIRE_LOCATION": "Bắt buộc đối chiếu GPS khi sinh viên tự điểm danh",
    "SELF_CHECKIN_MAX_ACCURACY_M": "Sai số GPS tối đa chấp nhận, tính bằng mét",
    "LOGIN_RATE_LIMIT": "Giới hạn số lần đăng nhập theo địa chỉ IP",
    "LOGIN_MAX_FAILED_PER_ACCOUNT": "Số lần sai mật khẩu tối đa cho một tài khoản",
    "LOGIN_FAILED_WINDOW_MINUTES": "Cửa sổ thời gian đếm số lần đăng nhập sai",
    "OTP_EXPIRE_MINUTES": "Thời hạn mã OTP đặt lại mật khẩu",
    "APP_UTC_OFFSET_MINUTES": "Múi giờ gắn vào mốc thời gian trả về cho client",
    "BACKGROUND_JOBS_ENABLED": "Bật hoặc tắt vòng lặp nền dọn ảnh và tự động đóng phiên",
    "ROOM_MIN_RADIUS_M": "Bán kính tối thiểu khi đối chiếu GPS theo toạ độ riêng của phòng, bù sai số GPS trong nhà",
    "CHECKIN_QR_ROTATE_SECONDS": "Chu kỳ đổi mã QR điểm danh chiếu trong phòng, tính bằng giây",
    "SELF_CHECKIN_REQUIRE_QR_DEFAULT": "Mặc định phiên mới có bắt buộc quét mã QR khi tự điểm danh",
    "APP_PUBLIC_URL": "Địa chỉ công khai của ứng dụng, dùng cho đường link trong email và mã QR điểm danh",
    "NOTIFY_EMAIL_INTERVAL_SECONDS": "Chu kỳ quét hàng đợi gửi email thông báo cho phụ huynh",
    "NOTIFY_EMAIL_MAX_ATTEMPTS": "Số lần thử gửi một email thông báo trước khi đánh dấu thất bại",
}
# Tham so ha tang, khong dua vao bang cau hinh nghiep vu cua bao cao.
BO_QUA_CAU_HINH = {
    "DATABASE_URL", "SECRET_KEY", "ALGORITHM", "EVIDENCE_DIR", "CORS_ORIGINS",
    "ANTISPOOF_MODEL_PATH", "SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD",
    "MAIL_FROM",
}

MO_TA_BANG = {
    "users": "Tài khoản đăng nhập dùng chung cho mọi vai trò",
    "units": "Đơn vị: Khoa, Phòng Đào tạo, Phòng CTSV, Ban ngành",
    "staff": "Hồ sơ cán bộ, mỗi cán bộ thuộc đúng một đơn vị",
    "students": "Hồ sơ sinh viên; đồng ý sinh trắc: phiên bản, cách ghi nhận, người ghi nhận",
    "lecturers": "Hồ sơ giảng viên",
    "classes": "Lớp học phần trong một học kỳ",
    "enrollments": "Ghi danh sinh viên vào lớp học phần",
    "locations": "Địa điểm điểm danh kèm bán kính cho phép",
    "schedules": "Lịch học cố định theo thứ trong tuần",
    "attendance_sessions": "Phiên điểm danh của một lịch học trong một ngày",
    "attendance_records": "Bản ghi điểm danh của từng sinh viên trong phiên",
    "attendance_audits": "Nhật ký mỗi lần sửa trạng thái điểm danh",
    "face_embeddings": "Vector đặc trưng khuôn mặt 512 chiều và trạng thái duyệt",
    "revoked_tokens": "Access token đã bị thu hồi trước hạn",
    "refresh_tokens": "Refresh token của app mobile, lưu bản băm và xoay vòng",
    "password_resets": "Yêu cầu đặt lại mật khẩu bằng OTP",
    "parents": "Tài khoản phụ huynh",
    "parent_students": "Liên kết phụ huynh với sinh viên",
    "rooms": "Phòng học thuộc một địa điểm, có thể có toạ độ và bán kính riêng",
    "notifications": "Thông báo điểm danh gửi phụ huynh, kèm trạng thái gửi email",
    "audit_logs": "Nhật ký hệ thống: người thao tác, hành động, đối tượng, Khoa liên quan",
}

MO_TA_TEST = {
    "test_auth.py": "Đăng nhập, sai mật khẩu, giới hạn số lần thử",
    "test_tokens_and_media.py": "Thu hồi token, xoay vòng refresh token, đường dẫn ảnh ký điện tử",
    "test_password_reset.py": "Quên và đặt lại mật khẩu bằng OTP",
    "test_authorization.py": "Quyền theo vai trò trên các endpoint chính",
    "test_unit_roles.py": "Vai trò theo đơn vị, phạm vi Khoa, Văn phòng Khoa và Lãnh đạo Khoa",
    "test_admin_crud.py": "Thêm, sửa, xoá các danh mục quản trị",
    "test_admin_management.py": "Quản lý tài khoản cán bộ và đơn vị",
    "test_face_approval.py": "Duyệt và từ chối dữ liệu khuôn mặt, xoá ảnh tạm",
    "test_consent.py": "Bắt buộc đồng ý sinh trắc: phiên bản, bản giấy, rút đồng ý, chặn nhận diện",
    "test_antispoof.py": "Chống giả mạo, kể cả khi thiếu tệp mô hình",
    "test_confirm_frames.py": "Xác nhận đa khung hình trước khi ghi điểm danh",
    "test_open_session_rules.py": "Điều kiện mở phiên theo khung giờ của tiết học",
    "test_session_lifecycle.py": "Vòng đời phiên: mở, điểm danh, đóng, sinh bản ghi vắng",
    "test_session_detail_and_records.py": "Chi tiết phiên, sửa điểm danh và nhật ký sửa",
    "test_location_checkin.py": "Tự điểm danh kèm đối chiếu toạ độ GPS",
    "test_my_attendance_detail.py": "Chuyên cần của sinh viên và của phụ huynh",
    "test_reports.py": "Báo cáo chuyên cần theo lớp",
    "test_reports_export_and_warnings.py": "Cảnh báo vắng và xuất tệp Excel",
    "test_week_schedule.py": "Thời khoá biểu theo tuần",
    "test_evidence_cleanup.py": "Dọn ảnh bằng chứng quá hạn lưu trữ",
    "test_flow_fixes.py": "Các lỗi luồng nghiệp vụ đã phát hiện và sửa",
    "test_audit_log.py": "Ghi nhật ký tự động, che trường nhạy cảm, phạm vi xem của Lãnh đạo Khoa",
    "test_change_password.py": "Đổi mật khẩu, thu hồi phiên đăng nhập cũ",
    "test_manager_reset_password.py": "Cán bộ đặt lại mật khẩu: quyền từng vai trò, thu hồi phiên, huỷ OTP, mở khoá",
    "test_checkin_qr.py": "Mã QR xoay vòng dạng link, mã 6 số dự phòng, chặn mã hết hạn",
    "test_parent_notifications.py": "Thông báo điểm danh cho phụ huynh và hàng đợi email",
    "test_rooms.py": "Danh mục phòng học, chặn trùng phòng, đối chiếu GPS theo phòng",
}

CHUA_MO_TA = "(chưa mô tả)"

# Cac doan ma nguon duoc trich vao baocao/code/ de \lstinputlisting nap vao bao cao.
# Trich thang tu file that nen doan ma in trong bao cao luon khop voi he thong.
# Chu thich tieng Viet bi luoc bo theo quy cach trinh bay ma nguon cua khoa.
TRICH_MA = [
    {"nguon": "backend/app/services/face_service.py", "ham": "recognize_frame",
     "dich": "nhan-dien-khung-hinh.py"},
    {"nguon": "backend/app/services/geo_service.py", "ham": "check_checkin_location",
     "dich": "doi-chieu-vi-tri.py"},
    {"nguon": "backend/app/core/authz.py", "ham": "filter_students",
     "dich": "loc-pham-vi-sinh-vien.py"},
]


# ---------------------------------------------------------------------------
#  Tien ich
# ---------------------------------------------------------------------------
def tex_escape(text: str) -> str:
    """Thoat ky tu dac biet cua LaTeX trong chuoi lay tu ma nguon."""
    thay = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$",
            "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}",
            "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}
    return "".join(thay.get(c, c) for c in text)


def so_viet(gia_tri) -> str:
    """0.45 -> '0{,}45'; 1500 -> '1.500' (dau thap phan/phan nghin kieu Viet).

    Dau phay thap phan boc trong cap ngoac: trong che do toan LaTeX coi dau phay la
    dau ngat cau va chen them khoang trang ('0, 45'), boc ngoac thi khong. O che do
    van ban ket qua khong doi.
    """
    if isinstance(gia_tri, bool):
        return "Bật" if gia_tri else "Tắt"
    if isinstance(gia_tri, float):
        return f"{gia_tri:g}".replace(".", "{,}")
    if isinstance(gia_tri, int):
        return f"{gia_tri:,}".replace(",", ".")
    return str(gia_tri)


def so_latex(gia_tri) -> str:
    """Gia tri san sang dat vao file .tex: so giu nguyen, chuoi thi thoat ky tu dac biet."""
    if isinstance(gia_tri, (bool, int, float)):
        return so_viet(gia_tri)
    return tex_escape(so_viet(gia_tri))


def doc(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def dem_dong_code(thu_muc: Path, duoi: str, bo_qua=("__pycache__", ".dart_tool", "build")) -> int:
    tong = 0
    for f in thu_muc.rglob(f"*{duoi}"):
        if any(phan in bo_qua for phan in f.parts):
            continue
        tong += sum(1 for _ in doc(f).splitlines())
    return tong


def trich_ham(noi_dung: str, ten_ham: str) -> str:
    """Cat than mot ham cap cao nhat ra khoi file .py, bo docstring va chu thich."""
    dong = noi_dung.splitlines()
    bat_dau = next((i for i, d in enumerate(dong) if d.startswith(f"def {ten_ham}(")), None)
    if bat_dau is None:
        raise ValueError(f"Khong tim thay ham {ten_ham}")
    ket_thuc = len(dong)
    for i in range(bat_dau + 1, len(dong)):
        if dong[i] and not dong[i][0].isspace() and not dong[i].startswith(")"):
            ket_thuc = i
            break
    than = dong[bat_dau:ket_thuc]

    ket_qua, trong_docstring = [], False
    for d in than:
        if trong_docstring:
            if '"""' in d:
                trong_docstring = False
            continue
        rut_gon = d.strip()
        if rut_gon.startswith('"""'):
            # Docstring mot dong hay nhieu dong deu bo.
            trong_docstring = rut_gon.count('"""') == 1
            continue
        if rut_gon.startswith("#"):
            continue
        if "  # " in d and '"' not in d.split("  # ")[1]:
            d = d.split("  # ")[0].rstrip()
        if d.strip():
            ket_qua.append(d.rstrip())
    while ket_qua and not ket_qua[-1].strip():
        ket_qua.pop()
    return "\n".join(ket_qua) + "\n"


def git(*args: str) -> str:
    try:
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                              text=True, timeout=20).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


# ---------------------------------------------------------------------------
#  Quet ma nguon
# ---------------------------------------------------------------------------
RE_ENDPOINT = re.compile(r'@router\.(get|post|put|patch|delete)\(\s*"([^"]*)"')
RE_PREFIX = re.compile(r'APIRouter\(\s*prefix="([^"]*)"')
RE_MODEL = re.compile(r'^class\s+(\w+)\(Base\):', re.M)
RE_TABLE = re.compile(r'__tablename__\s*=\s*"([^"]+)"')
RE_SETTING = re.compile(r'^    ([A-Z][A-Z0-9_]*)\s*:\s*[\w\[\] |]+\s*=\s*(.+?)\s*(?:#\s*(.*))?$', re.M)
RE_ROLE = re.compile(r'^ROLE_[A-Z_]+\s*=\s*"([^"]+)"', re.M)
RE_CONSENT_VERSION = re.compile(r'^CONSENT_VERSION\s*=\s*"([^"]+)"', re.M)
RE_TEST = re.compile(r'^def (test_\w+)', re.M)


def quet_api() -> list[dict]:
    modules = []
    for f in sorted((ROOT / "backend/app/api").glob("*.py")):
        if f.name == "__init__.py":
            continue
        noi_dung = doc(f)
        endpoints = RE_ENDPOINT.findall(noi_dung)
        if not endpoints:
            continue
        prefix = RE_PREFIX.search(noi_dung)
        # Router khong khai bao prefix (vd media): lay doan dau cua duong dan lam nhan.
        goc = "/" + endpoints[0][1].lstrip("/").split("/")[0]
        modules.append({
            "ten": f.stem,
            "prefix": prefix.group(1) if prefix else goc,
            "so_endpoint": len(endpoints),
            "duong_dan": sorted({f"{m.upper()} {p or '/'}" for m, p in endpoints}),
        })
    return modules


def quet_bang_du_lieu() -> list[dict]:
    """Ghep ten lop ORM voi __tablename__ cua no, theo dung thu tu trong models.py."""
    noi_dung = doc(ROOT / "backend/app/db/models.py")
    ket_qua = []
    for khop in RE_MODEL.finditer(noi_dung):
        ket_thuc = noi_dung.find("\nclass ", khop.end())
        than_lop = noi_dung[khop.end():ket_thuc if ket_thuc != -1 else len(noi_dung)]
        bang = RE_TABLE.search(than_lop)
        if bang:
            ket_qua.append({"lop": khop.group(1), "bang": bang.group(1)})
    return ket_qua


def quet_cau_hinh() -> dict:
    noi_dung = doc(ROOT / "backend/app/core/config.py")
    ket_qua = {}
    for ten, gia_tri, chu_thich in RE_SETTING.findall(noi_dung):
        gia_tri = gia_tri.strip().rstrip(",")
        if gia_tri.startswith('"') and gia_tri.endswith('"'):
            doc_ra = gia_tri[1:-1]
        elif gia_tri in ("True", "False"):
            doc_ra = gia_tri == "True"
        else:
            try:
                doc_ra = float(gia_tri) if "." in gia_tri else int(gia_tri)
            except ValueError:
                doc_ra = gia_tri
        ket_qua[ten] = {"gia_tri": doc_ra, "chu_thich": (chu_thich or "").strip()}
    return ket_qua


def quet_test() -> dict:
    thu_muc = ROOT / "backend/tests"
    files = {}
    for f in sorted(thu_muc.glob("test_*.py")):
        files[f.name] = len(RE_TEST.findall(doc(f)))
    return files


def quet_man_hinh_flutter() -> dict:
    goc = ROOT / "mobile/lib/features"
    nhom = {}
    for thu_muc in sorted(p for p in goc.iterdir() if p.is_dir()):
        nhom[thu_muc.name] = sorted(p.stem for p in thu_muc.glob("*.dart"))
    return nhom


def quet_ma_trich() -> dict:
    """Trich cac doan ma nguon can in trong bao cao, tra ve {ten file dich: noi dung}."""
    ket_qua = {}
    for muc in TRICH_MA:
        ket_qua[muc["dich"]] = trich_ham(doc(ROOT / muc["nguon"]), muc["ham"])
    return ket_qua


def quet() -> dict:
    api = quet_api()
    bang = quet_bang_du_lieu()
    cau_hinh = quet_cau_hinh()
    test = quet_test()
    man_hinh = quet_man_hinh_flutter()
    vai_tro = RE_ROLE.findall(doc(ROOT / "backend/app/db/models.py"))
    migration = sorted(p.stem.split("_")[0]
                       for p in (ROOT / "backend/alembic/versions").glob("*.py"))
    return {
        "ngay_quet": datetime.now().strftime("%d/%m/%Y"),
        "git": {
            "commit": git("rev-parse", "--short", "HEAD"),
            "nhanh": git("rev-parse", "--abbrev-ref", "HEAD"),
            "so_commit": git("rev-list", "--count", "HEAD"),
            "ngay_commit": git("log", "-1", "--format=%ad", "--date=format:%d/%m/%Y"),
        },
        "api": api,
        "bang_du_lieu": bang,
        "cau_hinh": cau_hinh,
        "test": test,
        "man_hinh": man_hinh,
        "vai_tro": vai_tro,
        "migration": migration,
        # Chi luu ban bam cua tung doan ma trich: du de biet doan ma da doi ma khong
        # phinh file hien-trang.json.
        "ma_trich": {ten: hashlib.sha1(noi_dung.encode("utf-8")).hexdigest()[:10]
                     for ten, noi_dung in quet_ma_trich().items()},
        "dong_python": dem_dong_code(ROOT / "backend/app", ".py"),
        "dong_dart": dem_dong_code(ROOT / "mobile/lib", ".dart"),
        "dong_test": dem_dong_code(ROOT / "backend/tests", ".py"),
        "phien_ban_dong_y": (RE_CONSENT_VERSION.findall(doc(ROOT / "backend/app/core/consent.py"))
                             or ["n/a"])[0],
    }


# ---------------------------------------------------------------------------
#  Sinh file LaTeX
# ---------------------------------------------------------------------------
def sinh_macro(d: dict) -> str:
    ch = {k: v["gia_tri"] for k, v in d["cau_hinh"].items()}
    tong_endpoint = sum(m["so_endpoint"] for m in d["api"])
    tong_test = sum(d["test"].values())
    tong_man_hinh = sum(len(v) for v in d["man_hinh"].values())

    macro = {
        # Qui mo he thong
        "FsoEndpoint": tong_endpoint,
        "FsoModuleApi": len(d["api"]),
        "FsoBang": len(d["bang_du_lieu"]),
        "FsoMigration": len(d["migration"]),
        "FsoVaiTro": len(d["vai_tro"]),
        "FsoTest": tong_test,
        "FsoFileTest": len(d["test"]),
        "FsoManHinh": tong_man_hinh,
        "FsoNhomManHinh": len(d["man_hinh"]),
        "FsoDongPython": d["dong_python"],
        "FsoDongDart": d["dong_dart"],
        "FsoDongTest": d["dong_test"],
        # Moc kho ma nguon
        "FcommitCuoi": d["git"]["commit"] or "n/a",
        "FnhanhGit": d["git"]["nhanh"] or "n/a",
        "FsoCommit": d["git"]["so_commit"] or "0",
        "FngayCommit": d["git"]["ngay_commit"] or d["ngay_quet"],
        "FngayQuet": d["ngay_quet"],
        # Tham so nhan dien
        "FchieuVector": 512,
        "FnguongNhanDien": ch.get("RECOGNITION_THRESHOLD", 0),
        "FnguongTrung": ch.get("DUPLICATE_THRESHOLD", 0),
        "FnguongThat": ch.get("ANTISPOOF_THRESHOLD", 0),
        "FsoKhungXacNhan": ch.get("CONFIRM_FRAMES", 0),
        # Tham so nghiep vu
        "FphutMuon": ch.get("LATE_AFTER_MINUTES", 0),
        "FphutMoSom": ch.get("EARLY_OPEN_MINUTES", 0),
        "FphutAnHan": ch.get("SESSION_GRACE_MINUTES", 0),
        "FngayLuuAnh": ch.get("EVIDENCE_RETENTION_DAYS", 0),
        "FphutHetHanUrl": ch.get("MEDIA_URL_EXPIRE_MINUTES", 0),
        "FphutToken": ch.get("ACCESS_TOKEN_EXPIRE_MINUTES", 0),
        "FngayRefresh": ch.get("REFRESH_TOKEN_EXPIRE_DAYS", 0),
        "FsaiSoGps": ch.get("SELF_CHECKIN_MAX_ACCURACY_M", 0),
        "FphutOtp": ch.get("OTP_EXPIRE_MINUTES", 0),
        "FsoLanSaiToiDa": ch.get("LOGIN_MAX_FAILED_PER_ACCOUNT", 0),
        "FbanKinhPhong": ch.get("ROOM_MIN_RADIUS_M", 0),
        "FgiayDoiQr": ch.get("CHECKIN_QR_ROTATE_SECONDS", 0),
        "FsoLanGuiEmail": ch.get("NOTIFY_EMAIL_MAX_ATTEMPTS", 0),
        # Phien ban noi dung dong y sinh trac hoc (backend/app/core/consent.py)
        "FphienBanDongY": d.get("phien_ban_dong_y", "n/a"),
    }
    ti_le = ch.get("ABSENCE_WARN_RATIO", 0)
    macro["FtiLeCanhBao"] = so_viet(round(float(ti_le) * 100)) if ti_le else "0"

    dong = [
        "% File nay do baocao/tools/quet-du-an.py sinh ra. KHONG SUA TAY.",
        f"% Lan quet gan nhat: {d['ngay_quet']} tren commit {d['git']['commit']}.",
        "% Sinh lai:  python baocao/tools/quet-du-an.py",
        "",
    ]
    for ten, gia_tri in macro.items():
        dong.append(f"\\newcommand{{\\{ten}}}{{{so_latex(gia_tri)}}}")
    return "\n".join(dong) + "\n"


def boc_macro(ten_lenh: str, dong: list[str], nguon: str) -> str:
    """Boc cac dong cua bang vao mot lenh LaTeX.

    Khong dung \\input thang trong than bang: tabularx quet than bang nhieu luot nen
    \\input o trong se lam vo can le ("Misplaced \\noalign"). Boc thanh lenh, nap o
    preamble roi goi ten lenh trong bang thi khong gap van de do.
    """
    dau = [f"% Sinh tu {nguon}. KHONG SUA TAY.", f"\\newcommand{{\\{ten_lenh}}}{{%"]
    return "\n".join(dau + dong + ["}"]) + "\n"


def sinh_bang_api(d: dict) -> str:
    dong = []
    for m in d["api"]:
        mo_ta = MO_TA_MODULE.get(m["ten"], CHUA_MO_TA)
        dong.append(f"\\code{{{tex_escape(m['prefix'])}}} & {m['so_endpoint']} & "
                    f"{tex_escape(mo_ta)} \\\\")
    return boc_macro("BangApi", dong, "doi tuong APIRouter trong backend/app/api/")


def sinh_bang_cau_hinh(d: dict) -> str:
    dong = []
    for ten, thong_tin in d["cau_hinh"].items():
        if ten in BO_QUA_CAU_HINH:
            continue
        mo_ta = MO_TA_CAU_HINH.get(ten) or thong_tin["chu_thich"] or CHUA_MO_TA
        dong.append(f"\\code{{{tex_escape(ten)}}} & {so_latex(thong_tin['gia_tri'])} & "
                    f"{tex_escape(mo_ta)} \\\\")
    return boc_macro("BangCauHinh", dong, "backend/app/core/config.py")


def sinh_bang_du_lieu(d: dict) -> str:
    dong = []
    for b in d["bang_du_lieu"]:
        mo_ta = MO_TA_BANG.get(b["bang"], CHUA_MO_TA)
        dong.append(f"\\code{{{tex_escape(b['bang'])}}} & {tex_escape(mo_ta)} \\\\")
    return boc_macro("BangDuLieu", dong, "backend/app/db/models.py")


def sinh_bang_test(d: dict) -> str:
    dong = []
    for ten, so_ca in sorted(d["test"].items(), key=lambda x: -x[1]):
        mo_ta = MO_TA_TEST.get(ten, CHUA_MO_TA)
        dong.append(f"\\code{{{tex_escape(ten)}}} & {so_ca} & {tex_escape(mo_ta)} \\\\")
    return boc_macro("BangTest", dong, "backend/tests/")


# ---------------------------------------------------------------------------
#  So lech voi lan quet truoc
# ---------------------------------------------------------------------------
def _tap_endpoint(d: dict) -> set:
    return {f"{m['prefix']} {dp}" for m in d["api"] for dp in m["duong_dan"]}


def so_lech(cu: dict | None, moi: dict) -> list[str]:
    if not cu:
        return ["Lan quet dau tien, chua co moc de so sanh."]
    ghi_chu = []

    def them(nhan: str, truoc: set, sau: set, goi_y: str):
        for x in sorted(sau - truoc):
            ghi_chu.append(f"- **Them {nhan}**: `{x}` -> {goi_y}")
        for x in sorted(truoc - sau):
            ghi_chu.append(f"- **Bo {nhan}**: `{x}` -> {goi_y}")

    them("endpoint", _tap_endpoint(cu), _tap_endpoint(moi),
         "ra soat Chuong 3 (thiet ke API) va Phu luc")
    them("bang du lieu", {b["bang"] for b in cu["bang_du_lieu"]},
         {b["bang"] for b in moi["bang_du_lieu"]},
         "cap nhat luoc do CSDL o Chuong 3")
    them("tham so cau hinh", set(cu["cau_hinh"]), set(moi["cau_hinh"]),
         "cap nhat bang tham so va phan giai thich o Chuong 4")
    them("vai tro", set(cu["vai_tro"]), set(moi["vai_tro"]),
         "cap nhat ma tran phan quyen o Chuong 3 va slide")
    them("migration", set(cu["migration"]), set(moi["migration"]),
         "nhac trong Chuong 4 neu doi luoc do")
    them("nhom man hinh", set(cu["man_hinh"]), set(moi["man_hinh"]),
         "cap nhat mo ta giao dien o Chuong 4")

    for ten, thong_tin in moi["cau_hinh"].items():
        cu_gia_tri = cu["cau_hinh"].get(ten, {}).get("gia_tri")
        if ten in cu["cau_hinh"] and cu_gia_tri != thong_tin["gia_tri"]:
            ghi_chu.append(f"- **Doi gia tri**: `{ten}` {cu_gia_tri} -> {thong_tin['gia_tri']} "
                           "-> soat lai cau van neu co dan con so nay")

    for ten, ban_bam in moi.get("ma_trich", {}).items():
        if cu.get("ma_trich", {}).get(ten) not in (None, ban_bam):
            ghi_chu.append(f"- **Doan ma trich doi**: `{ten}` -> doc lai phan giai thich "
                           "doan ma nay o Chuong 4")

    cu_test, moi_test = sum(cu["test"].values()), sum(moi["test"].values())
    if cu_test != moi_test:
        ghi_chu.append(f"- **So test doi**: {cu_test} -> {moi_test} -> cap nhat Chuong 5 "
                       "(ket qua kiem thu)")

    thieu_mo_ta = [m["ten"] for m in moi["api"] if m["ten"] not in MO_TA_MODULE]
    thieu_mo_ta += [t for t in moi["cau_hinh"]
                    if t not in MO_TA_CAU_HINH and t not in BO_QUA_CAU_HINH]
    thieu_mo_ta += [b["bang"] for b in moi["bang_du_lieu"] if b["bang"] not in MO_TA_BANG]
    thieu_mo_ta += [t for t in moi["test"] if t not in MO_TA_TEST]
    for x in thieu_mo_ta:
        ghi_chu.append(f"- **Thieu mo ta tieng Viet**: `{x}` -> them vao tu dien trong "
                       "baocao/tools/quet-du-an.py")

    return ghi_chu or ["Khong co thay doi nao anh huong toi bao cao."]


# ---------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(description="Sinh so lieu bao cao FAMS tu ma nguon")
    parser.add_argument("--kiem-tra", action="store_true",
                        help="Chi kiem tra, khong ghi file. Thoat 1 neu so lieu da cu.")
    args = parser.parse_args()

    moi = quet()
    cu = None
    file_json = AUTO_DIR / "hien-trang.json"
    if file_json.exists():
        try:
            cu = json.loads(doc(file_json))
        except json.JSONDecodeError:
            cu = None

    ghi_chu = so_lech(cu, moi)
    # Bo qua thoi diem quet khi so sanh: chi quan tam noi dung du an.
    da_cu = cu is None or {k: v for k, v in cu.items() if k not in ("ngay_quet", "git")} != \
        {k: v for k, v in moi.items() if k not in ("ngay_quet", "git")}

    if args.kiem_tra:
        print("\n".join(ghi_chu))
        if da_cu:
            print("\n[LECH] So lieu trong baocao/auto/ da cu. Chay: "
                  "python baocao/tools/quet-du-an.py")
            return 1
        print("\n[OK] So lieu bao cao khop voi ma nguon.")
        return 0

    AUTO_DIR.mkdir(parents=True, exist_ok=True)
    for ten_file, noi_dung in (
        ("du-lieu-du-an.tex", sinh_macro(moi)),
        ("bang-api.tex", sinh_bang_api(moi)),
        ("bang-cau-hinh.tex", sinh_bang_cau_hinh(moi)),
        ("bang-bang-du-lieu.tex", sinh_bang_du_lieu(moi)),
        ("bang-test.tex", sinh_bang_test(moi)),
    ):
        (AUTO_DIR / ten_file).write_text(noi_dung, encoding="utf-8")

    thu_muc_ma = BAOCAO_DIR / "code"
    thu_muc_ma.mkdir(parents=True, exist_ok=True)
    for ten, noi_dung in quet_ma_trich().items():
        (thu_muc_ma / ten).write_text(noi_dung, encoding="utf-8")

    (AUTO_DIR / "thay-doi.md").write_text(
        "# Thay doi so voi lan quet truoc\n\n"
        f"Quet luc {moi['ngay_quet']} tren commit {moi['git']['commit']} "
        f"(nhanh {moi['git']['nhanh']}).\n\n" + "\n".join(ghi_chu) + "\n",
        encoding="utf-8")
    file_json.write_text(json.dumps(moi, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Da sinh lai so lieu trong {AUTO_DIR}")
    print("\n".join(ghi_chu))
    return 0


if __name__ == "__main__":
    sys.exit(main())
