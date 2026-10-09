# Triển khai FAMS lên máy chủ để có link cố định

> **Không có thẻ ngân hàng quốc tế?** Dùng [tailscale/HUONG-DAN.md](tailscale/HUONG-DAN.md)
> — miễn phí vĩnh viễn, không cần thẻ, chạy ngay trên máy của bạn (link chỉ sống khi máy bật).

Kết quả cuối: một địa chỉ dạng `https://fams-dnu.duckdns.org` chạy liên tục, mở được
từ bất cứ đâu, camera và quét mã QR hoạt động (trình duyệt chỉ cho dùng camera trên HTTPS).

Hướng dẫn này viết cho **Oracle Cloud Always Free** vì đây là lựa chọn duy nhất vừa miễn
phí vĩnh viễn vừa đủ mạnh cho nhận diện khuôn mặt. Các bước tương tự với bất kỳ máy chủ
Linux nào — chỉ khác phần mở cổng ở mục 2.

---

## 1. Tạo máy ảo

Trong Oracle Cloud, tạo Instance với:

| Mục | Chọn |
| --- | --- |
| Shape | **Ampere A1 Compute** (ARM) — thuộc gói Always Free |
| Cấu hình | 2 OCPU / 12 GB RAM trở lên |
| Hệ điều hành | Ubuntu 22.04 hoặc 24.04 |
| Ổ cứng | 50 GB trở lên |

Nhớ **tải tệp khóa SSH** lúc tạo máy — mất là không vào được nữa, phải tạo máy khác.

Sau khi máy chạy, vào *Networking → Reserved Public IPs* gán cho máy một **IP tĩnh**.
IP mặc định là loại tạm, khởi động lại máy có thể đổi — link sẽ chết.

## 2. Mở cổng 80 và 443

Đây là chỗ hay mắc nhất ở Oracle: phải mở ở **hai nơi**, thiếu một là không truy cập được.

**Nơi thứ nhất — Security List của mạng ảo:** vào *Networking → Virtual Cloud Networks →
VCN đang dùng → Security Lists → Default Security List*, thêm hai Ingress Rule:

- Source `0.0.0.0/0`, IP Protocol `TCP`, Destination Port Range `80`
- Source `0.0.0.0/0`, IP Protocol `TCP`, Destination Port Range `443`

**Nơi thứ hai — tường lửa trong Ubuntu.** Ảnh Ubuntu của Oracle chặn sẵn mọi cổng bằng
iptables. SSH vào máy rồi chạy:

```bash
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
sudo netfilter-persistent save
```

## 3. Trỏ tên miền về máy chủ

Chưa có tên miền thì dùng [DuckDNS](https://www.duckdns.org) (miễn phí): đăng nhập bằng
GitHub, tạo một tên như `fams-dnu`, điền IP tĩnh ở bước 1 vào ô *current ip*, bấm update.

Tên miền của bạn sẽ là `fams-dnu.duckdns.org`. Kiểm tra đã trỏ đúng chưa:

```bash
ping -c 2 fams-dnu.duckdns.org
```

Phải thấy đúng IP máy chủ thì mới sang bước tiếp. Caddy cần điều này để xin được chứng chỉ.

## 4. Cài Docker

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
```

Thoát SSH rồi vào lại để quyền có hiệu lực.

## 5. Lấy mã nguồn

Repo đang để riêng tư nên cần Personal Access Token của GitHub (*Settings → Developer
settings → Personal access tokens → Tokens (classic)*, chọn quyền `repo`):

```bash
git clone https://github.com/jfgafgfagfbja/FAMS.git
cd FAMS
```

Khi được hỏi mật khẩu thì dán token vào (GitHub không nhận mật khẩu tài khoản nữa).

## 6. Cấu hình

```bash
cp deploy/.env.example deploy/.env
openssl rand -hex 32          # chép kết quả vào SECRET_KEY
nano deploy/.env
```

Phải điền: `FAMS_DOMAIN`, `SECRET_KEY`, `POSTGRES_PASSWORD`. Ba giá trị này không có
mặc định — thiếu là compose báo lỗi ngay thay vì chạy với cấu hình yếu.

## 7. Chạy

```bash
docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env up -d --build
```

Lần đầu **mất 30–60 phút** trên máy ARM: phải biên dịch `insightface` từ mã nguồn và tải
bộ Flutter SDK để build giao diện. Các lần sau chỉ vài phút nhờ bộ nhớ đệm.

Theo dõi tiến trình:

```bash
docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env logs -f
```

Khi backend khởi động lần đầu, nó tự tải model nhận diện `buffalo_l` (~300 MB).

## 8. Đổi hết mật khẩu — làm ngay, trước khi đưa link cho ai

Dữ liệu mẫu đang dùng mật khẩu rất yếu (`admin123`, `gv123`, `sv123`). Link đã công khai
thì ai cũng thử đăng nhập được, và vào rồi là xem được ảnh khuôn mặt lẫn dữ liệu điểm danh.

```bash
docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env \
    exec backend python tools/doi_mat_khau.py
```

Lệnh này đặt mật khẩu ngẫu nhiên cho toàn bộ tài khoản, thu hồi mọi phiên đăng nhập cũ,
và ghi mật khẩu mới ra `mat_khau_moi.csv` **bên trong container**. Lấy tệp đó ra máy mình:

```bash
docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env \
    cp backend:/app/mat_khau_moi.csv ./mat_khau_moi.csv
docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env \
    exec backend rm /app/mat_khau_moi.csv
```

Gửi mật khẩu cho từng người rồi **xóa tệp CSV** — nó để mật khẩu dạng chữ rõ.

Muốn xem trước có bao nhiêu tài khoản bị ảnh hưởng mà chưa đổi gì: thêm `--chi-xem`.

## 9. Kiểm tra

Mở `https://fams-dnu.duckdns.org` trên điện thoại. Cần thấy:

- Ổ khóa HTTPS trên thanh địa chỉ (Caddy đã xin được chứng chỉ)
- Đăng nhập được bằng mật khẩu mới
- Giảng viên mở phiên → bật *Yêu cầu quét mã QR* → chiếu mã; sinh viên quét được

Chứng chỉ không xin được thì gần như chắc chắn do bước 2 hoặc 3: cổng chưa mở, hoặc
tên miền chưa trỏ đúng IP. Xem log của Caddy:

```bash
docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env logs caddy
```

---

## Cập nhật khi có mã nguồn mới

```bash
cd FAMS && git pull
docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env up -d --build
```

Migration tự chạy lúc backend khởi động (`entrypoint.sh`), không cần làm gì thêm.

## Sao lưu cơ sở dữ liệu

Dữ liệu nằm trong volume Docker, xóa máy ảo là mất sạch. Sao lưu định kỳ:

```bash
docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env \
    exec -T db pg_dump -U fams fams | gzip > fams-$(date +%F).sql.gz
```

Ảnh bằng chứng điểm danh nằm trong volume `evidence`, sao lưu riêng nếu cần giữ.

## Những điều nên biết trước

- **Máy ARM.** Một vài thư viện Python phải biên dịch thay vì tải sẵn, nên lần build đầu
  lâu. Nếu `insightface` báo lỗi lúc cài, thường là thiếu RAM — chọn shape từ 12 GB trở lên.
- **Oracle thu hồi máy không dùng.** Tài khoản Always Free bị lấy lại máy ảo nếu để nhàn
  rỗi nhiều ngày liên tục. Hệ thống có người dùng thật thì không sao.
- **Ảnh khuôn mặt là dữ liệu cá nhân.** Khi hệ thống chạy công khai, ảnh sinh viên nằm trên
  máy chủ ngoài trường. Nếu dùng với sinh viên thật, nên xin phép nhà trường trước.
