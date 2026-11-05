# Link công khai cố định cho FAMS bằng Tailscale Funnel

Kết quả: một địa chỉ dạng `https://fams.tailxxxx.ts.net`, có HTTPS (camera và quét QR chạy
được), **miễn phí vĩnh viễn**, không cần thẻ ngân hàng.

Đổi lại: **link chỉ sống khi máy này đang bật** và đã bấm khởi động bản công khai.

## Máy này đang có hai bản FAMS tách biệt

| | Bản phát triển | Bản công khai |
| --- | --- | --- |
| Địa chỉ | `localhost:5173`, `localhost:5180` | Link Tailscale |
| Cơ sở dữ liệu | `fams` | `fams_public` |
| Mật khẩu | `sv123`, `gv123`, `admin123`... | Mật khẩu mạnh trong `D:\fams-trien-khai\mat_khau_ban_cong_khai.csv` |
| Ai vào được | Chỉ chính máy này | Bất kỳ ai có link |

Bản công khai chỉ nghe trên `127.0.0.1:7860` — người ngoài chỉ đi vào được qua Tailscale,
không ai gọi thẳng vào máy bạn được.

---

## Cài đặt lần đầu (~10 phút)

### Bước 1 — Cài Tailscale

Mở https://tailscale.com/download/windows → tải về → chạy tệp cài đặt → bấm qua các bước.

### Bước 2 — Đăng nhập

Sau khi cài, biểu tượng Tailscale hiện ở khay hệ thống (góc dưới bên phải, có thể nằm
trong mũi tên ^). Bấm vào → **Log in** → trình duyệt mở ra → **Sign in with Google**.

Nếu được hỏi dùng cho cá nhân hay công việc, chọn **Personal use**. Khi trình duyệt hỏi
có kết nối máy này không, bấm **Connect**.

### Bước 3 (nên làm) — Đặt tên máy cho link đẹp

Link có dạng `https://<tên-máy>.<tên-mạng>.ts.net`. Mặc định tên máy là tên Windows (kiểu
`desktop-a1b2c3`), trông không gọn khi đưa vào báo cáo.

Mở https://login.tailscale.com/admin/machines → bấm **⋯** ở dòng máy này → **Edit machine
name** → tắt *Auto-generate from OS hostname* → gõ `fams` → **Update name**.

**Làm bước này trước khi đưa link vào báo cáo** — đổi tên máy là đổi link.

### Bước 4 — Bật bản công khai

Mở thư mục `D:\FAMS\deploy\tailscale\` → **bấm đúp** `bat-fams-cong-khai.cmd`.

**Lần đầu tiên**, cửa sổ sẽ hiện một dòng kiểu:

```
Funnel is not enabled on your tailnet.
To enable, visit:
         https://login.tailscale.com/f/funnel?node=...
```

Mở đường link đó → bấm **Enable**. Quay lại cửa sổ, nó tự chạy tiếp và cuối cùng in ra:

```
 LINK CONG KHAI: https://fams.tailxxxx.ts.net
```

**Đây là link cố định của bạn.** Từ lần thứ hai trở đi không còn hỏi duyệt nữa.

### Bước 5 — Thử từ bên ngoài

Trên điện thoại, **tắt Wi-Fi, dùng 4G** (để chắc là đi qua Internet chứ không phải mạng
nhà), mở link, đăng nhập bằng một tài khoản trong tệp CSV.

---

## Dùng hằng ngày

| Muốn | Làm |
| --- | --- |
| Bật link (sau khi khởi động lại máy) | Bấm đúp `bat-fams-cong-khai.cmd` |
| Tắt link | Bấm đúp `tat-fams-cong-khai.cmd` |

Bấm bật nhiều lần cũng không sao — phần nào đang chạy rồi thì nó bỏ qua.

**Trước buổi bảo vệ:** vào *Settings → System → Power* của Windows, đặt **Sleep: Never**.
Máy ngủ là link chết.

## Khi có lỗi

| Hiện tượng | Xử lý |
| --- | --- |
| `LOI: Chua cai Tailscale` | Làm lại bước 1 |
| `LOI: Chua co CSDL fams_public` | Cơ sở dữ liệu công khai bị xóa (ví dụ do `docker compose down -v`). Nạp lại từ `D:\fams-trien-khai\fams_public.sql` |
| `LOI: Ban cong khai khong khoi dong duoc` | Mở tệp `D:\fams-trien-khai\fams_public.err.log` xem dòng cuối |
| Link mở ra báo không kết nối được | Máy đang tắt/ngủ, hoặc chưa bấm `bat-fams-cong-khai.cmd` |
| **Máy tính vào được, điện thoại thì không** | Tên miền chưa lên DNS công khai — máy này luôn vào được qua mạng nội bộ của Tailscale nên không tự thấy lỗi. Cửa sổ bật link sẽ in dòng `CANH BAO: DNS cong khai CHUA co...`. Chờ 10 phút; vẫn vậy thì bấm tắt rồi bật lại và chờ thêm 10 phút. Trên điện thoại, bật/tắt chế độ máy bay để xóa kết quả cũ |
| Đăng nhập báo sai mật khẩu | Đang dùng mật khẩu bản phát triển — bản công khai dùng mật khẩu trong CSV |

## Những điều nên biết

- **Ảnh khuôn mặt mẫu trong trang duyệt khuôn mặt không hiện** ở bản công khai, vì thư
  mục ảnh được tách riêng. Nhận diện vẫn chạy bình thường — dữ liệu khuôn mặt nằm trong
  cơ sở dữ liệu, không phụ thuộc ảnh.
- **Dữ liệu là bản chụp tại thời điểm chuẩn bị.** Sửa dữ liệu ở bản phát triển không tự
  sang bản công khai, và ngược lại.
- **Giao diện cũng là bản chụp** (`D:\fams-trien-khai\web`). Muốn cập nhật bản công khai
  sau khi sửa code: build web, chép đè thư mục đó, rồi tắt và bật lại.
- **Xóa tệp `mat_khau_ban_cong_khai.csv`** sau khi đã gửi mật khẩu cho mọi người.
