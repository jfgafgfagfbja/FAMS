---
name: bao-cao-fams
description: Cập nhật quyển báo cáo LaTeX và bộ slide bảo vệ trong baocao/ cho khớp với hiện trạng dự án FAMS. Dùng khi backend, app Flutter, cơ sở dữ liệu hoặc cấu hình vừa thay đổi, khi người dùng nói "cập nhật báo cáo", "đồng bộ báo cáo với code", "viết lại chương ... của đồ án", hoặc trước khi nộp và bảo vệ đồ án. Cũng dùng khi cần thêm mục mới vào báo cáo hay slide.
---

# Cập nhật cặp báo cáo + slide của đồ án FAMS

Thư mục `baocao/` chứa hai tài liệu dùng chung một nguồn số liệu:

- `do-an.tex` — quyển báo cáo, 5 chương + phụ lục, theo mẫu AIP202 của Khoa CNTT.
- `slide.tex` — slide bảo vệ, lớp `beamer`, 16:9.

Số liệu trong cả hai đến từ `auto/`, do `tools/quet-du-an.py` sinh ra bằng
cách đọc thẳng mã nguồn. Nhiệm vụ của skill này là giữ **phần văn xuôi** khớp
với phần số liệu đó.

## Quy trình

Làm đúng thứ tự sau, không bỏ bước.

### 1. Quét lại dự án

```bash
python baocao/tools/quet-du-an.py
```

Lệnh này sinh lại `auto/*.tex`, `code/*.py` và ghi `auto/thay-doi.md`.

### 2. Đọc những gì đã đổi

Đọc `baocao/auto/thay-doi.md`. Đây là danh sách thay đổi so với lần quét
trước, mỗi dòng đã kèm gợi ý mục nào trong báo cáo cần soát lại. Nếu tệp báo
"Khong co thay doi nao anh huong toi bao cao" thì chỉ cần làm bước 5 rồi
dừng, đừng sửa văn xuôi cho có.

Khi dòng thay đổi nói **"Thieu mo ta tieng Viet"**: mở
`baocao/tools/quet-du-an.py`, thêm mô tả tiếng Việt (có dấu) vào đúng từ điển
`MO_TA_MODULE`, `MO_TA_CAU_HINH`, `MO_TA_BANG` hoặc `MO_TA_TEST`, rồi chạy
lại bước 1.

### 3. Sửa văn xuôi theo bảng ánh xạ

| Thay đổi trong mã nguồn | Chỗ cần soát lại |
|---|---|
| Thêm hoặc bỏ endpoint | `chuong/03-phan-tich-thiet-ke.tex` mục thiết kế API |
| Thêm hoặc bỏ bảng dữ liệu | `chuong/03` mục thiết kế CSDL, và ba quyết định thiết kế bên dưới bảng |
| Đổi vai trò hoặc ma trận quyền | `chuong/03` mục phân quyền, bảng trong `slide.tex` frame "Phân quyền hai chiều" |
| Thêm hoặc đổi tham số cấu hình | `chuong/04-cai-dat.tex` mục tham số cấu hình |
| Đoạn mã trích đổi | `chuong/04` phần giải thích ngay dưới đoạn mã đó |
| Đổi luồng nghiệp vụ điểm danh | `chuong/03` giải thuật, `slide.tex` frame về chống gian lận |
| Thêm nhóm màn hình Flutter | `chuong/04` bảng nhóm màn hình |
| Số test đổi | `chuong/05-ket-qua-danh-gia.tex` mục kiểm thử |
| Thêm tính năng lớn | `chuong/01` mục tiêu nếu phạm vi đổi, `chuong/05` đối chiếu mục tiêu và hướng phát triển, và slide phần Kết quả |

### 4. Giữ đúng các quy ước

- **Không sửa tay** bất cứ tệp nào trong `baocao/auto/` hay `baocao/code/`.
  Muốn đổi nội dung ở đó thì sửa `tools/quet-du-an.py` rồi chạy lại.
- **Không sửa** `styles/dau.sty`, `styles/settings.tex`, `styles/slide-dau.sty`.
- **Không gõ tay con số** nào mà công cụ đã có lệnh tương ứng. Dùng
  `\FsoEndpoint`, `\FsoBang`, `\FsoTest`, `\FnguongNhanDien`… Xem danh sách
  đầy đủ trong `auto/du-lieu-du-an.tex`.
- **Không bịa số đo.** Hiệu năng, độ chính xác nhận diện, kết quả chống giả
  mạo, kết quả `pytest` phải đo thật. Những ô đó đang là `\cando{...}` và giữ
  nguyên cho tới khi có số thật. Riêng bảng hiệu năng thì chạy
  `cd backend && python tools/do_hieu_nang.py --anh-mot-mat <ảnh> --ghi`,
  công cụ tự ghi `baocao/auto/bang-hieu-nang.tex` và Chương 5 tự dùng file đó.
- Văn xuôi tiếng Việt có dấu. Chú thích bên trong khối mã nguồn in ra báo cáo
  thì bằng tiếng Anh, theo quy cách của Khoa.
- Thuật ngữ tiếng Anh chèn trong câu dùng `\en{...}`, tên biến và tên tệp
  dùng `\code{...}`, nhớ thoát dấu gạch dưới thành `\_`.
- Mỗi chương mở đầu bằng khối `\begin{muctieu}`. Giữ nguyên cấu trúc đó.
- Sửa quyển báo cáo thì soát luôn slide, và ngược lại. Hai tài liệu phải kể
  cùng một câu chuyện.

### 5. Kiểm tra

```bash
python baocao/tools/quet-du-an.py --kiem-tra
python baocao/tools/kiem-tra-tex.py
powershell -ExecutionPolicy Bypass -File baocao\tools\build.ps1
```

Hai lệnh đầu phải thoát sạch. Lệnh thứ ba build thật ra PDF bằng MiKTeX và in
số lỗi, số chỗ tràn lề, số trang — **luôn chạy lệnh này trước khi báo là
xong**, đừng chỉ dựa vào kiểm tra tĩnh.

Ba cái bẫy đã gặp, đừng lặp lại:

- Không đặt `\input` bên trong `tabularx`. Bảng sinh tự động phải bọc thành
  lệnh, nạp ở preamble của `do-an.tex`, thân bảng chỉ gọi tên lệnh.
- Node TikZ có `\\` thì tikzpicture phải khai báo
  `every node/.append style={align=center}`, vì các style `io`, `process`,
  `decision`, `startstop` trong `dau.sty` chỉ có `text centered`.
- Trong beamer, `\begin{itemize}[...]` chỉ nhận overlay kiểu `<+->`, không
  nhận khoá của gói `enumitem` như `itemsep=3pt`.

### 6. Báo lại cho người dùng

Nói ngắn gọn: đã quét lại gì, mục nào trong báo cáo và slide đã sửa, còn chỗ
`\cando` nào đang chờ số đo thật.

## Khi được yêu cầu thêm nội dung mới

Thêm một mục vào chương: viết trực tiếp vào tệp chương tương ứng, theo đúng
giọng văn đang có (câu khẳng định, giải thích lý do thiết kế, tránh liệt kê
suông). Thêm một slide: chèn `\begin{frame}{Tiêu đề}` vào đúng phần, giữ mật
độ chữ thấp, ưu tiên `\solon{con số}{nhãn}`, bảng ngắn hoặc sơ đồ TikZ.

Nếu nội dung mới cần một con số lấy từ mã nguồn mà công cụ chưa có, hãy thêm
lệnh mới vào hàm `sinh_macro` trong `tools/quet-du-an.py` thay vì gõ số trực
tiếp vào tệp `.tex`.
