import io
import json
import logging
import datetime as dt

import httpx
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from app.config import settings
from app import store

logger = logging.getLogger(__name__)

API = "https://api.telegram.org/bot"
PENDING_CATEGORY: dict[int, dict] = {}  # telegram_id -> tx draft


def _api_url(method: str) -> str:
    return f"{API}{settings.telegram_bot_token}/{method}"


async def _call(method: str, payload: dict) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        res = await client.post(_api_url(method), json=payload)
        res.raise_for_status()
        return res.json()


async def send_message(chat_id: int, text: str, reply_markup: dict | None = None):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    await _call("sendMessage", payload)


def _category_keyboard(categories: list[dict]) -> dict:
    buttons = [
        [{"text": f"{c['emoji'] or ''} {c['name']}".strip(), "callback_data": c["id"]}]
        for c in categories
    ]
    return {"inline_keyboard": buttons}


def _fmt_money(v: float) -> str:
    if v >= 1_000_000_000:
        return f"{v / 1_000_000_000:.1f} tỷ"
    if v >= 1_000_000:
        s = f"{v / 1_000_000:.1f} tr".replace(".0 tr", " tr")
        return s
    if v >= 1_000:
        s = f"{v / 1_000:.0f}k"
        return s
    return f"{v:.0f}đ"


def _is_allowed(telegram_id: int) -> bool:
    allowed = settings.allowed_ids
    return not allowed or telegram_id in allowed


async def handle_update(update: dict):
    message = update.get("message")
    callback = update.get("callback_query")
    source = callback or message
    if not source:
        return
    if not _is_allowed(source["from"]["id"]):
        return
    if callback:
        await handle_callback(callback)
    elif message:
        await handle_message(message)


async def handle_message(message: dict):
    chat_id = message["chat"]["id"]
    telegram_id = message["from"]["id"]
    name = message["from"].get("first_name")

    user_id = store.ensure_user(telegram_id, name)

    if message.get("photo") or message.get("document"):
        await handle_photo(message, user_id)
        return

    text = (message.get("text") or "").strip()
    if not text:
        return

    if text.startswith("/"):
        await handle_command(chat_id, user_id, text, message.get("from", {}).get("first_name"))
        return

    from app.parser import parse_message
    parsed = parse_message(text)
    if not parsed:
        await send_message(
            chat_id,
            "Không hiểu được số tiền. Ví dụ: <b>50k ăn trưa</b>, <b>1tr tiền điện</b>, hoặc <b>+15tr lương</b>",
        )
        return

    tx_type = "income" if parsed["is_income"] else "expense"
    tx = store.save_transaction(user_id, parsed["amount"], tx_type, parsed["note"])
    cats = store.get_categories(user_id)
    PENDING_CATEGORY[telegram_id] = {"tx_id": tx["id"], "user_id": user_id}
    sign = "+" if tx_type == "income" else "-"
    reply = f"Đã ghi: {sign}{_fmt_money(parsed['amount'])} {parsed['note'] or ''}\nChọn nhóm:"

    if tx_type == "expense":
        budget = store.get_budget(user_id)
        if budget:
            today = dt.date.today()
            summary = store.get_month_summary(user_id, today.year, today.month)
            spent = summary["total_expense"]
            pct = spent / budget * 100
            if pct >= 100:
                reply = f"🚨 VƯỢT HẠN MỨC!\n{reply}\n\nĐã chi {spent:,.0f}đ / {budget:,.0f}đ ({pct:.0f}%)"
            elif pct >= 80:
                reply = f"⚠️ Cảnh báo: đã chi {pct:.0f}% hạn mức ({spent:,.0f}đ / {budget:,.0f}đ)\n{reply}"

    await send_message(
        chat_id,
        reply,
        reply_markup=_category_keyboard(cats),
    )


async def handle_photo(message: dict, user_id: str):
    chat_id = message["chat"]["id"]
    telegram_id = message["from"]["id"]

    photo = message.get("photo")
    if photo:
        file_id = photo[-1]["file_id"]  # kích thước lớn nhất
    else:
        doc = message.get("document", {})
        if not doc.get("mime_type", "").startswith("image/"):
            await send_message(chat_id, "Chỉ nhận ảnh làm hóa đơn.")
            return
        file_id = doc["file_id"]

    file_info = await _call("getFile", {"file_id": file_id})
    file_path = file_info["result"]["file_path"]
    download_url = f"https://api.telegram.org/file/bot{settings.telegram_bot_token}/{file_path}"
    async with httpx.AsyncClient(timeout=60) as client:
        res = await client.get(download_url)
        res.raise_for_status()
        image_bytes = res.content

    url = store.upload_receipt(user_id, image_bytes, f"{file_id}.jpg")

    caption = (message.get("caption") or "").strip()
    if caption and not caption.startswith("/"):
        from app.parser import parse_message
        parsed = parse_message(caption)
        if parsed:
            tx_type = "income" if parsed["is_income"] else "expense"
            tx = store.save_transaction(
                user_id, parsed["amount"], tx_type, parsed["note"], image_url=url
            )
            cats = store.get_categories(user_id)
            PENDING_CATEGORY[telegram_id] = {"tx_id": tx["id"], "user_id": user_id}
            await send_message(
                chat_id,
                f"Đã ghi hóa đơn: {parsed['amount']:,.0f}đ {parsed['note'] or ''}\nChọn nhóm:",
                reply_markup=_category_keyboard(cats),
            )
            return

    PENDING_CATEGORY[telegram_id] = {"user_id": user_id, "image_url": url}
    await send_message(
        chat_id,
        "Đã lưu ảnh hóa đơn. Nhập số tiền + ghi chú (vd: <b>50k ăn trưa</b>) để hoàn tất giao dịch:",
    )


async def handle_callback(callback: dict):
    chat_id = callback["message"]["chat"]["id"]
    telegram_id = callback["from"]["id"]
    category_id = callback["data"]
    pending = PENDING_CATEGORY.pop(telegram_id, None)

    if not pending:
        await _call("answerCallbackQuery", {"callback_query_id": callback["id"]})
        await send_message(chat_id, "Không có giao dịch nào đang chờ. Gửi lại số tiền nhé.")
        return

    sb = store.get_client()
    if pending.get("tx_id"):
        sb.table("transactions").update({"category_id": category_id}).eq(
            "id", pending["tx_id"]
        ).execute()
        await _call("answerCallbackQuery", {"callback_query_id": callback["id"], "text": "Đã lưu!"})
        await send_message(chat_id, "✅ Xong!")
    elif pending.get("image_url"):
        # ảnh đã lưu, giờ cần số tiền — lưu category tạm, đợi user nhập số tiền
        pending["category_id"] = category_id
        PENDING_CATEGORY[telegram_id] = pending
        await _call("answerCallbackQuery", {"callback_query_id": callback["id"]})
        await send_message(chat_id, "Nhập số tiền + ghi chú (vd: <b>50k ăn trưa</b>):")
        # đánh dấu đang đợi amount cho ảnh
        pending["awaiting_amount"] = True
    else:
        await _call("answerCallbackQuery", {"callback_query_id": callback["id"]})


async def handle_command(chat_id: int, user_id: str, text: str, message_name: str | None = None):
    cmd = text.split()[0].split("@")[0].lower()
    today = dt.date.today()

    if cmd == "/start":
        await send_message(
            chat_id,
            "👋 Ghi chi tiêu kiểu:\n"
            "<b>50k ăn trưa</b>\n"
            "<b>1tr tiền điện</b>\n"
            "<b>+15tr lương</b>\n"
            "Gửi ảnh hóa đơn kèm caption vd: <b>50k cà phê</b>\n\n"
            "Lệnh: /today, /month, /undo (xóa giao dịch cuối), "
            "/budget 10tr (đặt hạn mức), /info (tổng quan), /help",
        )
    elif cmd in ("/info", "/status"):
        summary = store.get_month_summary(user_id, today.year, today.month)
        budget = store.get_budget(user_id)
        cats = store.get_categories(user_id)
        total_tx = len(summary["transactions"])
        with_image = sum(1 for t in summary["transactions"] if t.get("image_url"))

        lines = [
            "ℹ️ <b>Thông tin & cấu hình</b>",
            "",
            f"👤 User: <b>{message_name or 'bạn'}</b>",
            f"📅 Kỳ hiện tại: <b>Tháng {today.month}/{today.year}</b>",
            "",
            "— <b>Tình hình tháng này</b> —",
            f"💸 Chi: <b>{summary['total_expense']:,.0f}đ</b> ({summary['expense_count']} gd)",
            f"💰 Thu: <b>{summary['total_income']:,.0f}đ</b> ({summary['income_count']} gd)",
            f"🖼️ Có ảnh: {with_image}/{total_tx} giao dịch",
        ]
        if budget:
            spent = summary["total_expense"]
            pct = spent / budget * 100
            remaining = budget - spent
            lines += [
                "",
                "— <b>Hạn mức (budget)</b> —",
                f"🎯 {budget:,.0f}đ/tháng",
                f"Đã dùng: <b>{pct:.0f}%</b> ({spent:,.0f}đ)",
                f"Còn lại: <b>{remaining:,.0f}đ</b>" + (" 🚨" if remaining < 0 else " ⚠️" if pct >= 80 else ""),
            ]
        else:
            lines += ["", "🎯 Chưa đặt hạn mức — dùng /budget 10tr"]
        lines += [
            "",
            "— <b>Nhóm chi tiêu</b> —",
            " • ".join(f"{c['emoji'] or ''}{c['name']}" for c in cats[:10]),
            "",
            "— <b>Lệnh hữu dụng</b> —",
            "• <code>50k ăn trưa</code> — ghi chi tiêu",
            "• <code>+15tr lương</code> — ghi thu nhập",
            "• Ảnh + caption <code>45k cà phê</code> — ghi kèm hóa đơn",
            "• /today /month — xem nhanh",
            "• /undo — xóa giao dịch cuối",
            "• /budget 10tr — đặt hạn mức",
            "• /help — hướng dẫn",
        ]
        await send_message(chat_id, "\n".join(lines))
    elif cmd == "/today":
        summary = store.get_month_summary(user_id, today.year, today.month)
        today_txs = [t for t in summary["transactions"] if t["occurred_at"] == today.isoformat()]
        total = sum(float(t["amount"]) for t in today_txs if t["type"] == "expense")
        lines = [f"📅 Hôm nay: <b>{total:,.0f}đ</b> ({len(today_txs)} giao dịch)"]
        for t in today_txs:
            cat = (t.get("categories") or {}).get("name") or "Chưa phân loại"
            lines.append(f"• {t['amount']:,.0f}đ — {cat} — {t.get('note') or ''}")
        await send_message(chat_id, "\n".join(lines))
    elif cmd in ("/month", "/stats"):
        summary = store.get_month_summary(user_id, today.year, today.month)
        lines = [
            f"📊 Tháng {today.month}/{today.year}",
            f"💸 Chi: <b>{summary['total_expense']:,.0f}đ</b>",
            f"💰 Thu: <b>{summary['total_income']:,.0f}đ</b>",
        ]
        if summary["by_category"]:
            lines.append("\nTheo nhóm:")
            for cat, total in summary["by_category"][:8]:
                lines.append(f"• {cat}: {total:,.0f}đ")
        await send_message(chat_id, "\n".join(lines))
    elif cmd == "/undo":
        tx = store.get_last_transaction(user_id)
        if not tx:
            await send_message(chat_id, "Không có giao dịch nào để xóa.")
            return
        store.delete_transaction(user_id, tx["id"])
        sign = "+" if tx["type"] == "income" else "-"
        await send_message(
            chat_id,
            f"🗑️ Đã xóa: {sign}{tx['amount']:,.0f}đ {tx.get('note') or ''} ({tx['occurred_at']})",
        )
    elif cmd == "/budget":
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            budget = store.get_budget(user_id)
            if budget:
                summary = store.get_month_summary(user_id, today.year, today.month)
                pct = summary["total_expense"] / budget * 100
                await send_message(
                    chat_id,
                    f"🎯 Hạn mức tháng này: <b>{budget:,.0f}đ</b>\n"
                    f"Đã chi: <b>{summary['total_expense']:,.0f}đ</b> ({pct:.0f}%)\n"
                    f"Còn lại: <b>{budget - summary['total_expense']:,.0f}đ</b>\n\n"
                    f"Đặt lại: /budget 10tr",
                )
            else:
                await send_message(chat_id, "Chưa đặt hạn mức. Dùng: /budget 10tr")
            return
        from app.parser import parse_message
        parsed = parse_message(parts[1])
        if not parsed or parsed["amount"] <= 0:
            await send_message(chat_id, "Không hiểu số tiền. Ví dụ: /budget 10tr")
            return
        store.set_budget(user_id, parsed["amount"])
        await send_message(chat_id, f"🎯 Đã đặt hạn mức <b>{parsed['amount']:,.0f}đ</b>/tháng")
    elif cmd == "/help":
        await handle_command(chat_id, user_id, "/start", message_name)
    else:
        await send_message(chat_id, "Lệnh không rõ. Xem /help")


def render_category_pie(summary: dict) -> bytes:
    cats = [c for c, _ in summary["by_category"]]
    vals = [v for _, v in summary["by_category"]]
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.pie(vals, labels=cats, autopct="%1.0f%%", startangle=90)
    ax.set_title(f"Chi tiêu theo nhóm — tháng {dt.date.today().month}/{dt.date.today().year}")
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()
