"""Dọn hội thoại Telegram cá nhân: chat riêng, nhóm, kênh.

Cách dùng:
1. Lấy api_id/api_hash tại https://my.telegram.org (API development tools)
2. Chạy dry-run trước để xem danh sách:
   python3 scripts/telegram_cleanup.py --api-id XXX --api-hash XXX --dry-run
3. Xem file cleanup_dry_run.txt, bỏ tên người/nhóm muốn GIỮ vào --keep
4. Chạy xóa thật (thêm --yes):
   python3 scripts/telegram_cleanup.py --api-id XXX --api-hash XXX --yes

Lưu ý:
- Chat với BOT luôn được giữ (bao gồm money tracker bot)
- Xóa là VĨNH VIỄN, không hoàn tác được
- Script sleep 1.5s giữa mỗi lần xóa để tránh bị Telegram flag spam
"""

import argparse
import asyncio
import sys

try:
    from telethon import TelegramClient
    from telethon.tl.types import User, Chat, Channel
except ImportError:
    sys.exit("Cần cài: pip install telethon")


def parse_args():
    p = argparse.ArgumentParser(description="Dọn hội thoại Telegram")
    p.add_argument("--api-id", required=True, type=int)
    p.add_argument("--api-hash", required=True)
    p.add_argument("--dry-run", action="store_true", help="Chỉ liệt kê, không xóa")
    p.add_argument("--yes", action="store_true", help="Xóa thật (bắt buộc cho chế độ xóa)")
    p.add_argument("--keep", nargs="*", default=[], help="Tên (chứa đựng) cần giữ lại")
    p.add_argument("--session", default="cleanup_session", help="Tên file session")
    return p.parse_args()


async def main():
    args = parse_args()
    if not args.dry_run and not args.yes:
        sys.exit("Chế độ xóa cần --yes. Nếu chỉ muốn xem danh sách, dùng --dry-run.")

    client = TelegramClient(args.session, args.api_id, args.api_hash)
    await client.start()  # lần đầu sẽ hỏi số điện thoại + mã code

    targets = []  # (dialog, label, kind)
    async for dialog in client.iter_dialogs():
        entity = dialog.entity
        name = dialog.name or ""

        if any(k.lower() in name.lower() for k in args.keep):
            continue

        if isinstance(entity, User):
            if entity.bot:
                continue  # luôn giữ chat với bot
            kind = "private"
        elif isinstance(entity, Chat):
            kind = "group"
        elif isinstance(entity, Channel):
            kind = "channel" if entity.broadcast else "group"
        else:
            kind = "other"

        targets.append((dialog, name, kind))

    print(f"Tìm thấy {len(targets)} hội thoại sẽ bị xóa:\n")
    lines = []
    counts = {"private": 0, "group": 0, "channel": 0}
    for dialog, name, kind in targets:
        counts[kind] = counts.get(kind, 0) + 1
        line = f"[{kind:8}] {name}"
        print("  " + line)
        lines.append(line)
    print(f"\nChat riêng: {counts['private']} | Nhóm: {counts['group']} | Kênh: {counts['channel']}")

    if args.dry_run:
        with open("cleanup_dry_run.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        print("\nĐã lưu danh sách vào cleanup_dry_run.txt")
        print("Để GIỮ lại ai đó, chạy lại với: --keep 'Tên cần giữ' 'Tên khác'")
        print("Khi chắc chắn, chạy lại với --yes")
        await client.disconnect()
        return

    print(f"\nSẮP XÓA VĨNH VIỄN {len(targets)} hội thoại. Bắt đầu sau 5 giây (Ctrl+C để hủy)...")
    await asyncio.sleep(5)

    deleted = 0
    for i, (dialog, name, kind) in enumerate(targets, 1):
        try:
            await client.delete_dialog(dialog.entity)
            deleted += 1
            print(f"[{i}/{len(targets)}] ✅ Xóa: {name}")
        except Exception as e:
            print(f"[{i}/{len(targets)}] ❌ Lỗi '{name}': {e}")
        await asyncio.sleep(1.5)  # tránh rate limit

    print(f"\nHoàn tất: xóa {deleted}/{len(targets)} hội thoại.")
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
