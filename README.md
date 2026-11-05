# Money Tracker Bot

Telegram bot + web dashboard (PWA) để theo dõi chi tiêu cá nhân, dùng trên iPhone không cần build app iOS.

## Tính năng
- Ghi chi tiêu qua Telegram: `50k ăn trưa`, `1tr tiền điện`, `+15tr lương`
- Gửi ảnh hóa đơn kèm caption (tuỳ chọn)
- Thống kê trong chat: `/today`, `/month`
- Web dashboard: biểu đồ tròn theo nhóm, cột theo ngày, danh sách giao dịch kèm ảnh
- Cài lên màn hình iPhone: Safari → Share → Add to Home Screen

## Cấu trúc
```
app/
  config.py         # Cấu hình từ biến môi trường
  parser.py         # Parse tin nhắn kiểu Việt ("50k", "1tr")
  db.py             # Supabase client
  store.py          # CRUD giao dịch, upload ảnh
  telegram_bot.py   # Xử lý update Telegram
  main.py           # FastAPI: webhook + REST API + static web
web/                # Dashboard PWA (HTML/CSS/JS + Chart.js)
scripts/schema.sql  # Schema Postgres
tests/              # Unit test
```

## Cài đặt

1. **Supabase**: tạo project tại [supabase.com](https://supabase.com) (free), chạy `scripts/schema.sql` trong SQL Editor, tạo Storage bucket `receipts` (public).

2. **Telegram bot**: nhắn [@BotFather](https://t.me/BotFather) → `/newbot` → lấy token.

3. **File .env**:
```
TELEGRAM_BOT_TOKEN=xxx
TELEGRAM_WEBHOOK_SECRET=chuoi-bi-mat
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_KEY=service-role-key
DASHBOARD_PASSCODE=ma-khoa-cua-ban
ALLOWED_TELEGRAM_IDS=id-telegram-cua-ban
APP_BASE_URL=https://domain-deploy
```

4. **Chạy local**:
```
pip install -r requirements.txt
uvicorn app.main:app --reload
```

5. **Set webhook Telegram**:
```
curl "https://api.telegram.org/bot<TOKEN>/setWebhook" \
  -d "url=<APP_BASE_URL>/webhook/telegram" \
  -d "secret_token=<TELEGRAM_WEBHOOK_SECRET>"
```

6. **Deploy**: Render / Fly.io / Railway — chạy `uvicorn app.main:app`, set các biến môi trường ở bước 3.

## Lấy Telegram ID
Nhắn [@userinfobot](https://t.me/userinfobot) để biết ID của mình, đưa vào `ALLOWED_TELEGRAM_IDS` để chỉ mình dùng được bot.

## Test
```
python -m pytest tests/ -q
```
