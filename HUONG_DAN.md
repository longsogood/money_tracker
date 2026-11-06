# Money Tracker — Hướng dẫn sử dụng

Money Tracker gồm 2 phần: **Telegram bot** để ghi chi tiêu nhanh kèm ảnh hóa đơn, và **Web dashboard (PWA)** để xem thống kê, cài đặt lên màn hình iPhone như app thật.

---

## 1. Telegram Bot

Tìm bot trên Telegram: **@vietlong_money_tracking_bot** → bấm **Start** (bắt buộc lần đầu).

### 1.1. Ghi chi tiêu / thu nhập

Chỉ cần nhắn tin thường, bot tự hiểu:

| Bạn nhắn | Bot ghi |
|---|---|
| `50k ăn trưa` | 50.000đ chi, note "ăn trưa" |
| `1tr tiền điện` | 1.000.000đ chi |
| `50000 xăng xe` | 50.000đ (không cần chữ k) |
| `2,5tr mua áo` | 2,5 triệu (dấu phẩy OK) |
| `+15tr lương` | thu nhập 15 triệu |
| `thu 500k` | thu nhập 500k |

Sau khi ghi, bot hiện các nút bấm để chọn nhóm (🍜 Ăn uống, 🚗 Di chuyển...) — bấm 1 nút là xong.

### 1.2. Ghi kèm ảnh hóa đơn (tùy chọn)

**Cách 1 — ảnh + caption** (khuyên dùng):

> Đính kèm ảnh hóa đơn, caption: `45k tạp hóa`

**Cách 2 — gửi ảnh trống trước:**

> Gửi ảnh không caption → bot hỏi số tiền → nhắn `45k tạp hóa`

Ảnh được lưu vĩnh viễn, hiện làm nền lịch trên web (kiểu locket).

### 1.3. Các lệnh

| Lệnh | Chức năng |
|---|---|
| `/today` | Tổng chi hôm nay + từng giao dịch |
| `/month` | Tổng chi/thu tháng + theo từng nhóm |
| `/undo` | Xóa giao dịch cuối (ghi sai thì dùng cái này) |
| `/budget 10tr` | Đặt hạn mức chi 10 triệu/tháng |
| `/budget` | Xem tiến độ hạn mức |
| `/info` hoặc `/status` | Tổng quan: tháng này, budget, nhóm chi tiêu, danh sách lệnh |
| `/help` | Hướng dẫn |

### 1.4. Cảnh báo hạn mức

Khi ghi chi tiêu, bot tự nhắn:
- ⚠️ **khi chi đạt 80%** hạn mức tháng
- 🚨 **khi vượt 100%** hạn mức

### 1.5. An ninh

Chỉ Telegram ID được cấu hình trong `ALLOWED_TELEGRAM_IDS` dùng được bot — người lạ nhắn sẽ bị bỏ qua.

---

## 2. Web Dashboard (PWA)

### 2.1. Cài lên màn hình iPhone

1. Mở **Safari** → vào URL Render (dạng `https://money-tracker-xxxx.onrender.com`)
2. Nhập **mã truy cập** (biến `DASHBOARD_PASSCODE`)
3. Nút **Share** (vuông có mũi tên) → **Add to Home Screen**
4. Đặt tên "Money" → **Add**

Giờ icon nằm trên màn hình iPhone như app thật, mở full-screen không thanh địa chỉ.

### 2.2. Tab Thống kê 📊

| Phần | Ý nghĩa |
|---|---|
| **2 thẻ tổng** | Tổng chi / tổng thu tháng, kèm so sánh % với tháng trước (▲ đỏ = chi tăng, ▼ xanh = chi giảm) |
| **Thanh budget** 🎯 | Tiến độ hạn mức: xanh (< 80%) → vàng (≥ 80%) → đỏ (vượt) |
| **Biểu đồ đường** | Tổng chi theo từng tháng, 6 tháng gần nhất |
| **Biểu đồ vòng** | Tỷ trọng chi theo nhóm — "tiền đổ vào đâu nhiều nhất" |
| **Biểu đồ cột** | Chi theo từng ngày trong tháng |
| **Top khoản chi** | 5 giao dịch chi lớn nhất tháng |

### 2.3. Tab Lịch 🗓️

Lịch tháng kiểu locket:
- Ngày có **ảnh hóa đơn** → ảnh hiện làm nền ô ngày
- Overlay tổng tiền dạng gọn: `-50k` (chi), `+15tr` (thu)
- Ngày hôm nay viền tím

### 2.4. Tab Danh sách 📋

- **＋ Thêm giao dịch**: form chọn chi/thu, số tiền, ghi chú, nhóm, ngày
- **🔍 Tìm kiếm** theo ghi chú, **lọc** theo nhóm
- Badge **CHI** (đỏ) / **THU** (xanh) trên mỗi giao dịch
- **🗑️ Xóa** từng giao dịch
- Bấm **thumbnail ảnh** để xem phóng to

### 2.5. Chung

- Nút **‹ ›** trên đầu: chuyển tháng (áp dụng cho cả 3 tab)
- Nút **☀️/🌙** góc phải: đổi giao diện sáng/tối, tự nhớ lựa chọn
- Passcode lưu trong session — mở lại phải nhập (an toàn cho dữ liệu tài chính)

---

## 3. Vận hành & khắc phục sự cố

### Server ngủ (free tier Render)

Free tier Render **sleep sau 15 phút** không có request:
- Tin nhắn đầu tiên sau lúc ngủ chậm 30–50 giây (Telegram tự retry, tin **không mất**)
- Khắc phục: tạo cron ping miễn phí tại [cron-job.org](https://cron-job.org) trỏ về URL của bạn, chu kỳ 10 phút

### Sửa sai giao dịch

- Qua bot: `/undo` (xóa giao dịch cuối)
- Qua web: tab Danh sách → 🗑️

### Đổi passcode dashboard

Render Dashboard → Environment → sửa `DASHBOARD_PASSCODE` → Save.

### Backup dữ liệu

- Dữ liệu nằm trong **Supabase** (bảng `transactions`, `categories`, `users`)
- Ảnh nằm trong Supabase Storage bucket `receipts`
- Supabase Dashboard → Database → Backups (free tier giữ backup 7 ngày)

### Cấu trúc dự án

```
app/               Backend FastAPI
  main.py          Webhook Telegram + REST API + web tĩnh
  telegram_bot.py  Xử lý tin nhắn bot
  parser.py        Parse "50k", "1tr", "+15tr lương"
  store.py         CRUD giao dịch, upload ảnh (Supabase)
  config.py        Đọc cấu hình từ biến môi trường
web/               Dashboard PWA (HTML/CSS/JS + Chart.js)
scripts/           schema.sql + tiện ích (telegram_cleanup.py)
tests/             Unit test parser
```

### Biến môi trường (Render / .env)

| Biến | Ý nghĩa |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Token từ @BotFather |
| `TELEGRAM_WEBHOOK_SECRET` | Chuỗi bí mật xác thực webhook |
| `SUPABASE_URL` | URL project Supabase (không có `/rest/v1`) |
| `SUPABASE_SERVICE_KEY` | Service role key (`sb_secret_...`) |
| `DASHBOARD_PASSCODE` | Mã truy cập dashboard |
| `ALLOWED_TELEGRAM_IDS` | Telegram ID được dùng bot (cách nhau dấu phẩy) |
| `PYTHON_VERSION` | `3.13.7` (Render cần, tránh lỗi build) |
