# Báo cáo đồ án FAMS — quyển báo cáo + bộ slide

Cặp tài liệu nộp học phần AIP202, dựng trên mẫu báo cáo đồ án của Khoa Công
nghệ Thông tin, Trường Đại học Kiến trúc Đà Nẵng:

| Tài liệu | Tệp chính | Kết quả |
|---|---|---|
| Quyển báo cáo | `do-an.tex` | `do-an.pdf` — 5 chương + phụ lục |
| Slide bảo vệ | `slide.tex` | `slide.pdf` — 16:9, khoảng 20 slide |

Hai tài liệu dùng **chung một nguồn số liệu**: cùng nạp `auto/du-lieu-du-an.tex`
do `tools/quet-du-an.py` sinh ra từ mã nguồn thật, nên không bao giờ lệch nhau
và không bao giờ lệch với hệ thống.

## 1. Build

**Trên Overleaf** (nhanh nhất, không cần cài gì):

1. Nén cả thư mục `baocao/` thành zip, vào Overleaf chọn **New Project →
   Upload Project**, kéo tệp zip vào.
2. **Menu → Compiler → XeLaTeX**.
3. **Menu → Main document** chọn `do-an.tex` (đổi sang `slide.tex` khi muốn
   build slide).
4. Bấm **Recompile**.

**Trên máy Windows** (đã kiểm chứng với MiKTeX 25.12):

```bash
powershell -ExecutionPolicy Bypass -File baocao\tools\build.ps1
```

Script chạy đủ số lượt XeLaTeX và BibTeX cho cả hai tài liệu, rồi in số lỗi,
số chỗ tràn lề và số trang.

Chưa có MiKTeX thì cài trước, nhớ `--scope user` để không cần quyền quản trị:

```bash
winget install --id MiKTeX.MiKTeX --scope user
```

**Trên máy Linux hoặc macOS** (TeX Live 2023 trở lên):

```bash
cd baocao
latexmk -xelatex do-an.tex
latexmk -xelatex slide.tex
latexmk -c                    # dọn tệp trung gian
```

> `latexmk` là script Perl. Bản MiKTeX cài bằng winget **không kèm Perl**, nên
> trên Windows sẽ báo *could not find the script engine 'perl'* — dùng
> `build.ps1` ở trên, hoặc cài thêm Strawberry Perl nếu vẫn muốn latexmk.

> Máy không có phông **Noto Sans** thì mẫu tự lùi về Latin Modern, bản PDF vẫn
> build được nhưng khác kiểu chữ so với bản chuẩn. Overleaf có sẵn Noto Sans.

## 2. Tệp nào sửa, tệp nào không

| Đường dẫn | Sửa tay? | Nội dung |
|---|---|---|
| `do-an.tex` | **Sửa đầu tiên** | Họ tên, MSSV, lớp ở đầu tệp |
| `slide.tex` | **Sửa đầu tiên** | Cùng thông tin đó, khai báo ở đầu tệp |
| `chuong/*.tex` | Sửa nhiều nhất | Nội dung từng chương |
| `refs.bib` | Sửa khi thêm tài liệu | Danh mục tham khảo |
| `figs/` | Bỏ ảnh vào đây | Ảnh chụp màn hình, sơ đồ |
| `auto/*` | **KHÔNG sửa tay** | Số liệu sinh tự động, sửa tay sẽ bị ghi đè |
| `code/*` | **KHÔNG sửa tay** | Đoạn mã trích tự động từ `backend/` |
| `styles/dau.sty` | **KHÔNG sửa** | Nhận diện DAU cho quyển báo cáo |
| `styles/settings.tex` | **KHÔNG sửa** | Thiết lập chung |
| `styles/slide-dau.sty` | **KHÔNG sửa** | Nhận diện DAU cho slide |

## 3. Cập nhật khi dự án thay đổi

Mỗi khi backend hoặc app đổi, chạy:

```bash
python baocao/tools/quet-du-an.py
```

Công cụ quét thẳng mã nguồn và sinh lại:

| Tệp sinh ra | Nội dung |
|---|---|
| `auto/du-lieu-du-an.tex` | Các lệnh số liệu: `\FsoEndpoint`, `\FsoBang`, `\FnguongNhanDien`… |
| `auto/bang-api.tex` | Bảng nhóm endpoint (Chương 3) |
| `auto/bang-bang-du-lieu.tex` | Bảng lược đồ CSDL (Chương 3) |
| `auto/bang-cau-hinh.tex` | Bảng tham số cấu hình (Chương 4) |
| `auto/bang-test.tex` | Bảng nhóm kiểm thử (Chương 5) |
| `code/*.py` | Đoạn mã in trong Chương 4, trích thẳng từ `backend/` |
| `auto/thay-doi.md` | **Những gì đã đổi so với lần quét trước, kèm gợi ý mục nào cần viết lại** |

Số liệu tự khớp lại ngay sau khi chạy. Phần **văn xuôi** thì không: đọc
`auto/thay-doi.md` rồi sửa các chương được nhắc tới. Nếu dùng Claude Code,
gõ `/bao-cao-fams` để nó làm trọn quy trình này.

Kiểm tra trước khi build:

```bash
python baocao/tools/quet-du-an.py --kiem-tra   # số liệu còn khớp mã nguồn không
python baocao/tools/kiem-tra-tex.py            # cú pháp LaTeX, \ref, \cite
```

## 3b. Đo hiệu năng để điền bảng ở Chương 5

Bảng "Kết quả đo hiệu năng" không điền tay. Chạy công cụ đo, nó tự ghi
`auto/bang-hieu-nang.tex` và Chương 5 tự dùng file đó thay cho các ô
**CẦN BỔ SUNG**:

```bash
cd backend && python tools/do_hieu_nang.py --anh-mot-mat ../anh/mot-mat.jpg --anh-nhieu-mat ../anh/ca-lop.jpg --ghi
```

Cần hai ảnh thật chụp bằng đúng thiết bị sẽ dùng khi bảo vệ (một ảnh một
khuôn mặt, một ảnh nhiều khuôn mặt), và một cơ sở dữ liệu đã có dữ liệu mẫu.
Thiếu ảnh thì công cụ vẫn đo được phần truy vấn cơ sở dữ liệu và báo rõ phép
đo nào chưa làm được.

Cả hai thoát với mã 1 khi phát hiện vấn đề, nên cắm được vào CI.

Khi dự án có **module API, bảng dữ liệu, tham số cấu hình hoặc tệp kiểm thử
mới**, công cụ vẫn sinh đủ bảng nhưng đánh dấu `(chưa mô tả)` và liệt kê
trong `auto/thay-doi.md`. Thêm mô tả tiếng Việt vào các từ điển ở đầu
`tools/quet-du-an.py` là xong.

## 4. Trước khi nộp

- [ ] Chạy `python baocao/tools/quet-du-an.py` lần cuối.
- [ ] Tìm chuỗi **CẦN BỔ SUNG** trong `do-an.pdf` và `slide.pdf`, không được
      còn chỗ nào. Đó là các ô chờ số đo thật: hiệu năng, độ chính xác nhận
      diện, kết quả chống giả mạo, kết quả `pytest`.
- [ ] Điền họ tên, MSSV, lớp ở đầu `do-an.tex` và `slide.tex`.
- [ ] Chèn ảnh chụp màn hình vào `figs/`, mở phần hình đang bị chú thích ở
      `chuong/04-cai-dat.tex` và `slide.tex`.
- [ ] Đi hết danh sách tự kiểm ở Phụ lục D của quyển báo cáo.
