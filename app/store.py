from app.db import get_client
from app.config import settings


DEFAULT_CATEGORIES = [
    ("Ăn uống", "🍜"), ("Di chuyển", "🚗"), ("Mua sắm", "🛍️"), ("Hóa đơn", "🧾"),
    ("Giải trí", "🎮"), ("Sức khỏe", "💊"), ("Giáo dục", "📚"), ("Khác", "❓"),
    ("Lương", "💰"), ("Thưởng", "🎁"),
]


def ensure_user(telegram_id: int, name: str | None) -> str:
    sb = get_client()
    res = sb.table("users").select("id").eq("telegram_id", telegram_id).limit(1).execute()
    if res.data:
        return res.data[0]["id"]
    created = (
        sb.table("users")
        .insert({"telegram_id": telegram_id, "name": name})
        .execute()
    )
    user_id = created.data[0]["id"]
    sb.table("categories").insert(
        [{"user_id": user_id, "name": n, "emoji": e} for n, e in DEFAULT_CATEGORIES]
    ).execute()
    return user_id


def get_categories(user_id: str) -> list[dict]:
    sb = get_client()
    res = (
        sb.table("categories")
        .select("id,name,emoji")
        .eq("user_id", user_id)
        .order("name")
        .execute()
    )
    return res.data


def save_transaction(
    user_id: str,
    amount: float,
    tx_type: str,
    note: str,
    category_id: str | None = None,
    image_url: str | None = None,
    occurred_at: str | None = None,
) -> dict:
    sb = get_client()
    row = {
        "user_id": user_id,
        "amount": amount,
        "type": tx_type,
        "note": note or None,
        "category_id": category_id,
        "image_url": image_url,
    }
    if occurred_at:
        row["occurred_at"] = occurred_at
    res = sb.table("transactions").insert(row).execute()
    return res.data[0]


def upload_receipt(user_id: str, file_bytes: bytes, filename: str) -> str:
    sb = get_client()
    path = f"{user_id}/{filename}"
    sb.storage.from_(settings.storage_bucket).upload(
        path, file_bytes, {"content-type": "image/jpeg", "upsert": "true"}
    )
    return sb.storage.from_(settings.storage_bucket).get_public_url(path)


def get_last_transaction(user_id: str) -> dict | None:
    sb = get_client()
    res = (
        sb.table("transactions")
        .select("id,amount,type,note,occurred_at")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    return res.data[0] if res.data else None


def delete_transaction(user_id: str, tx_id: str):
    sb = get_client()
    sb.table("transactions").delete().eq("id", tx_id).eq("user_id", user_id).execute()


def set_budget(user_id: str, amount: float) -> float:
    sb = get_client()
    sb.table("users").update({"budget": amount}).eq("id", user_id).execute()
    return amount


def get_budget(user_id: str) -> float | None:
    sb = get_client()
    res = sb.table("users").select("budget").eq("id", user_id).limit(1).execute()
    val = res.data[0]["budget"] if res.data else None
    return float(val) if val is not None else None


def get_month_summary(user_id: str, year: int, month: int) -> dict:
    sb = get_client()
    start = f"{year:04d}-{month:02d}-01"
    if month == 12:
        end = f"{year + 1:04d}-01-01"
    else:
        end = f"{year:04d}-{month + 1:02d}-01"

    res = (
        sb.table("transactions")
        .select("amount,type,note,occurred_at,categories(name,emoji)")
        .eq("user_id", user_id)
        .gte("occurred_at", start)
        .lt("occurred_at", end)
        .order("occurred_at", desc=True)
        .execute()
    )
    rows = res.data
    expenses = [r for r in rows if r["type"] == "expense"]
    incomes = [r for r in rows if r["type"] == "income"]
    total_expense = sum(float(r["amount"]) for r in expenses)
    total_income = sum(float(r["amount"]) for r in incomes)

    by_cat: dict[str, float] = {}
    for r in expenses:
        cat = (r.get("categories") or {}).get("name") or "Khác"
        by_cat[cat] = by_cat.get(cat, 0.0) + float(r["amount"])

    return {
        "total_expense": total_expense,
        "total_income": total_income,
        "expense_count": len(expenses),
        "income_count": len(incomes),
        "by_category": sorted(
            by_cat.items(), key=lambda kv: kv[1], reverse=True
        ),
        "transactions": rows,
    }
