# FAMS Frontend

React 18 + Vite. Xem `../README.md` (root) de biet buc tranh toan du an.

## Chay dev

```bash
npm install
copy .env.example .env      # sua VITE_API_URL neu backend chay port khac 8000
npm run dev                 # http://localhost:5173
```

## Test & build

```bash
npm test                    # vitest
npm run build                # kiem tra build san xuat sach, xuat ra dist/
```

## Cau truc theo vai trò

| Route | Vai trò | Trang |
|---|---|---|
| `/login` | Ai cung vao duoc | Dang nhap |
| `/` | admin | Dashboard KPI toan truong |
| `/` | lecturer | Lop cua toi + lich day hom nay + mo phien diem danh |
| `/` | student | Diem danh cua toi (lich su + % vang) |
| `/attendance/:sessionId` | lecturer, admin | Man hinh diem danh realtime (webcam + overlay + roster) |
| `/sessions/:sessionId/records` | lecturer, admin | Xem & sua record sau buoi hoc |
| `/enroll` | ai cung vao duoc | Dang ky khuon mat (can consent) |
| `/students`, `/classes` | admin | CRUD sinh vien / lop / giang vien / lich hoc |
