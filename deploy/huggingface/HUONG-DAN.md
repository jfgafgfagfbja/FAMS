# Đưa FAMS lên Hugging Face để có link cố định

> **Lưu ý (10/2026):** Hugging Face đã chuyển Docker Space sang gói trả phí — cần gắn thẻ
> và mua PRO hoặc credit thì mới tạo được. Hướng dẫn này chỉ còn dùng được nếu bạn có tài
> khoản trả phí. Không có thẻ thì dùng [../tailscale/HUONG-DAN.md](../tailscale/HUONG-DAN.md).

Kết quả: một địa chỉ dạng `https://<tên-bạn>-fams.hf.space`, mở được bất cứ lúc nào,
kể cả khi máy bạn tắt. Không cần thẻ ngân hàng.

Gồm hai dịch vụ miễn phí:

- **Hugging Face** chạy ứng dụng (máy 2 nhân, 16 GB RAM — đủ cho nhận diện khuôn mặt).
- **Neon** giữ cơ sở dữ liệu PostgreSQL (có sẵn pgvector cho dữ liệu khuôn mặt).

Ba thứ đã chuẩn bị sẵn trong `D:\fams-trien-khai\`:

| Tệp | Là gì |
| --- | --- |
| `fams_public.sql` | Bản sao dữ liệu hiện có, **đã đổi hết mật khẩu** |
| `mat_khau_ban_cong_khai.csv` | Mật khẩu mới của 45 tài khoản trên bản công khai |
| `SECRET_KEY.txt` | Khóa bí mật cho bản công khai |

Mật khẩu ở máy bạn (`sv123`, `gv123`...) **không đổi** — chỉ bản công khai dùng mật khẩu mới.

---

## Bước 1 — Tạo token GitHub chỉ-đọc (~3 phút)

Hugging Face cần token này để tải mã nguồn từ repo riêng tư của bạn lúc build.

1. Mở https://github.com/settings/personal-access-tokens/new
2. **Token name:** `fams-huggingface`
3. **Expiration:** chọn *Custom* → một năm sau
4. **Repository access:** chọn *Only select repositories* → chọn **FAMS**
5. **Permissions → Repository permissions → Contents:** chọn **Read-only**
6. Bấm **Generate token** → **chép token ngay** (rời trang là không xem lại được)

Token này chỉ đọc được đúng repo FAMS, không sửa được gì.

## Bước 2 — Tạo cơ sở dữ liệu trên Neon (~5 phút)

1. Mở https://neon.tech → **Sign up** → đăng nhập bằng Google hoặc GitHub
2. Tạo project:
    - **Project name:** `fams`
    - **Postgres version:** **16**
    - **Region:** **AWS US East (N. Virginia)** — đặt gần máy chủ của Hugging Face cho nhanh
3. Ở trang tổng quan, tìm khung **Connection string**:
    - **Tắt** công tắc *Connection pooling*
    - Bấm **Copy** → được chuỗi dạng `postgresql://neondb_owner:...@ep-....neon.tech/neondb?sslmode=require`

Giữ chuỗi này, bước 3 và bước 5 đều cần.

## Bước 3 — Nạp dữ liệu vào Neon (1 lệnh)

Mở **Docker Desktop** và chờ nó báo *Engine running*. Sau đó mở **PowerShell** và chạy
lệnh dưới, thay `CHUOI_NEON` bằng chuỗi vừa chép — **giữ nguyên dấu ngoặc kép**:

```bash
docker run --rm -v D:\fams-trien-khai:/data pgvector/pgvector:pg16 psql "CHUOI_NEON" -v ON_ERROR_STOP=1 -q -f /data/fams_public.sql
```

Lệnh này mượn tạm công cụ `psql` trong ảnh Docker có sẵn trên máy, đọc tệp
`D:\fams-trien-khai\fams_public.sql` và gửi lên Neon, xong thì tự dọn. Không phụ thuộc
vào container cơ sở dữ liệu ở máy bạn.

Chạy xong không báo gì là thành công. Lệnh này chỉ chạy **một lần** trên cơ sở dữ liệu
trống; chạy lần hai sẽ báo lỗi bảng đã tồn tại, không hỏng gì.

## Bước 4 — Tạo Space trên Hugging Face (~3 phút)

1. Mở https://huggingface.co/join → đăng ký (email hoặc Google)
2. Mở https://huggingface.co/new-space
    - **Space name:** `fams`
    - **License:** để trống
    - **Select the Space SDK:** **Docker** → **Blank**
    - **Space hardware:** **CPU basic · Free**
    - **Public** (bắt buộc — để Private thì thầy cô phải có tài khoản Hugging Face mới vào được)
3. Bấm **Create Space**

Mã nguồn FAMS **không** nằm trong Space, nên để Public vẫn an toàn: người khác chỉ thấy
hai tệp cấu hình, không thấy code.

## Bước 5 — Khai báo 3 bí mật (~3 phút)

Trong Space vừa tạo: **Settings** → kéo xuống **Variables and secrets** → bấm
**New secret** ba lần:

| Name | Value |
| --- | --- |
| `GITHUB_TOKEN` | token ở bước 1 |
| `DATABASE_URL` | chuỗi Neon ở bước 2 |
| `SECRET_KEY` | nội dung tệp `D:\fams-trien-khai\SECRET_KEY.txt` |

Phải đúng chính xác tên ba bí mật (chữ hoa, gạch dưới).

## Bước 6 — Tải hai tệp lên Space (~2 phút)

Trong Space: tab **Files** → **+ Add file** → **Upload files** → kéo thả hai tệp từ
thư mục `D:\FAMS\deploy\huggingface\`:

- `Dockerfile`
- `README.md` (ghi đè tệp mặc định)

Bấm **Commit changes to main**.

## Bước 7 — Chờ build (~20–30 phút)

Hugging Face tự build ngay sau bước 6. Xem tiến trình ở tab **Logs** (góc trên bên
phải trang Space). Lâu là do phải tải bộ Flutter, biên dịch thư viện nhận diện khuôn mặt
và tải model 300 MB — chỉ lần đầu như vậy.

Trạng thái chuyển sang **Running** màu xanh là xong.

## Bước 8 — Lấy link cố định

Trên trang Space: nút **⋮** góc trên bên phải → **Embed this Space** → chép
**Direct URL**. Có dạng:

```
https://<tên-bạn>-fams.hf.space
```

**Đây là link đưa vào báo cáo.** Dùng link `.hf.space` chứ đừng dùng link
`huggingface.co/spaces/...` — link kia nhúng app trong khung, trình duyệt sẽ chặn camera.

Đăng nhập bằng mật khẩu trong `mat_khau_ban_cong_khai.csv`.

---

## Khi có lỗi

| Hiện tượng | Nguyên nhân thường gặp |
| --- | --- |
| Build đỏ, log có `Authentication failed` hoặc `Repository not found` | `GITHUB_TOKEN` sai, hết hạn, hoặc chưa cấp quyền Contents cho repo FAMS |
| Build đỏ, log có `secret ... not found` | Tên bí mật gõ sai — phải đúng `GITHUB_TOKEN` |
| Build xong nhưng Space báo lỗi khi chạy, log có `could not connect` | `DATABASE_URL` sai, hoặc quên tắt *Connection pooling* |
| Đăng nhập báo sai mật khẩu | Đang dùng mật khẩu cũ — bản công khai dùng mật khẩu trong tệp CSV |
| Trang báo đang khởi động | Space ngủ sau 2 ngày không ai vào; chờ 2–3 phút là tỉnh |

Chụp màn hình tab **Logs** gửi tôi là tôi đọc ra lỗi.

## Những điều nên biết

- **Ảnh bằng chứng điểm danh mất khi Space khởi động lại** — gói miễn phí không có ổ
  lưu trữ lâu dài. Dữ liệu điểm danh và khuôn mặt thì vẫn còn vì nằm ở Neon.
- **Dữ liệu là bản chụp tại thời điểm chuẩn bị.** Sửa dữ liệu ở máy bạn không tự cập
  nhật lên bản công khai.
- **Cập nhật mã nguồn:** push lên GitHub xong, vào Space → **Settings** →
  **Factory rebuild**.
- **Token GitHub hết hạn** thì bản đang chạy vẫn sống, chỉ lần build sau mới lỗi.
- **Xóa tệp `mat_khau_ban_cong_khai.csv`** sau khi đã gửi mật khẩu cho mọi người.
