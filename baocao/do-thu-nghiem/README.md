# Phiếu đếm cho hai thí nghiệm phải làm tay

Hai bảng ở Chương 5 cần người thật ngồi trước camera nên không tự động hoá
được. Làm thí nghiệm, đếm kết quả vào hai tệp CSV trong thư mục này, rồi chạy:

```bash
python baocao/tools/ghi-ket-qua-thu-nghiem.py
```

Script tính tỉ lệ, cộng dòng tổng hợp và ghi ra `auto/bang-do-chinh-xac.tex`,
`auto/bang-chong-gia-mao.tex`. Chương 5 tự dùng hai tệp đó. Dòng nào còn để
trống thì vẫn in **CẦN BỔ SUNG**, không bịa số.

## Thí nghiệm 1 — độ chính xác nhận diện (`do-chinh-xac.csv`)

Chuẩn bị: nhờ 3--5 bạn đăng ký khuôn mặt trong hệ thống. **Ảnh đăng ký và ảnh
thử phải chụp ở hai buổi khác nhau** — chụp liên tiếp trong cùng một phút sẽ
cho kết quả đẹp giả tạo, hội đồng hỏi là lộ.

Với mỗi điều kiện, cho từng bạn thử một số lần bằng nhau (gợi ý 10 lần mỗi
bạn), đếm số lần hệ thống hiện đúng tên:

| Điều kiện | Cách tạo điều kiện |
|---|---|
| Chính diện, đủ sáng | Ngồi đối diện camera trong phòng bật đèn |
| Nghiêng khoảng 30 độ | Quay mặt sang một bên chừng 30 độ |
| Thiếu sáng | Tắt bớt đèn, hoặc ngồi quay lưng về phía cửa sổ |
| Đeo kính | Bạn nào đăng ký lúc không đeo kính thì khi thử hãy đeo vào |
| Ngồi xa camera | Ngồi ở cuối phòng, khuôn mặt chiếm ít điểm ảnh |

Ghi vào CSV: `so_lan_thu` là tổng số lần thử của điều kiện đó (cộng hết các
bạn), `nhan_dung` là số lần ra đúng người.

## Thí nghiệm 2 — chống giả mạo (`chong-gia-mao.csv`)

**Cần tệp mô hình chống giả mạo**: `backend/models/2.7_80x80_MiniFASNetV2.onnx`
(xem `backend/models/README.md`). Thiếu tệp này thì hệ thống bỏ qua bước kiểm
tra và thí nghiệm không có ý nghĩa — kiểm tra trước khi ngồi đếm.

Lấy ảnh của một bạn đã đăng ký, rồi lần lượt:

1. **Ảnh in màu** — in ảnh chân dung ra giấy, giơ trước camera.
2. **Ảnh trên màn hình điện thoại** — mở ảnh trên điện thoại, giơ trước camera.
3. **Video phát lại** — quay một đoạn video khuôn mặt, phát lại trước camera.

Mỗi kiểu thử ít nhất 10 lần, đổi khoảng cách và góc nghiêng giữa các lần. Ghi
`so_lan_chan` là số lần hệ thống từ chối (báo nghi giả mạo, không ghi điểm
danh).

Nhớ đếm luôn số lần hệ thống **chặn nhầm người thật** trong cùng buổi, rồi
viết một câu vào phần bàn luận của Chương 5. Một mô hình chặn được mọi ảnh giả
nhưng cũng chặn luôn người thật thì không dùng được trong lớp học.
