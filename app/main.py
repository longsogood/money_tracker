import datetime as dt

from fastapi import FastAPI, HTTPException, Request, Header, Response
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.config import settings
from app import telegram_bot, store

app = FastAPI(title="Money Tracker")


@app.post("/webhook/telegram")
async def telegram_webhook(request: Request, x_telegram_bot_api_secret_token: str = Header(default="")):
    if settings.telegram_webhook_secret and x_telegram_bot_api_secret_token != settings.telegram_webhook_secret:
        raise HTTPException(status_code=403, detail="Invalid secret")
    update = await request.json()
    try:
        await telegram_bot.handle_update(update)
    except Exception:
        import traceback
        traceback.print_exc()
        return JSONResponse({"ok": True})
    return JSONResponse({"ok": True})


# ---------- Auth đơn giản cho dashboard ----------

def _check_passcode(passcode: str):
    if passcode != settings.dashboard_passcode:
        raise HTTPException(status_code=401, detail="Sai mã truy cập")


# ---------- REST API cho dashboard ----------

class LoginBody(BaseModel):
    passcode: str


@app.post("/api/login")
def login(body: LoginBody):
    _check_passcode(body.passcode)
    return {"ok": True}


def _get_user_id() -> str | None:
    sb = store.get_client()
    user = sb.table("users").select("id,budget").limit(1).execute()
    return user.data[0] if user.data else None


@app.get("/api/summary")
def summary(year: int | None = None, month: int | None = None, passcode: str = ""):
    _check_passcode(passcode)
    user = _get_user_id()
    empty = {"total_expense": 0, "total_income": 0, "by_category": [], "transactions": [], "expense_count": 0, "income_count": 0}
    if not user:
        return empty
    user_id = user["id"]
    today = dt.date.today()
    y, m = year or today.year, month or today.month

    result = store.get_month_summary(user_id, y, m)

    prev_y, prev_m = (y - 1, 12) if m == 1 else (y, m - 1)
    prev = store.get_month_summary(user_id, prev_y, prev_m)
    result["prev_total_expense"] = prev["total_expense"]
    result["prev_total_income"] = prev["total_income"]

    result["budget"] = float(user["budget"]) if user.get("budget") is not None else None
    return result


@app.get("/api/trend")
def trend(passcode: str = ""):
    _check_passcode(passcode)
    user = _get_user_id()
    if not user:
        return {"months": [], "expenses": []}
    sb = store.get_client()
    res = (
        sb.table("transactions")
        .select("amount,type,occurred_at")
        .eq("user_id", user["id"])
        .eq("type", "expense")
        .order("occurred_at")
        .execute()
    )
    by_month: dict[str, float] = {}
    for r in res.data:
        key = r["occurred_at"][:7]  # YYYY-MM
        by_month[key] = by_month.get(key, 0.0) + float(r["amount"])

    today = dt.date.today()
    months, expenses = [], []
    for i in range(5, -1, -1):
        m = dt.date(today.year, today.month, 1) - dt.timedelta(days=i * 31)
        # tính tháng chính xác
        y, mo = today.year, today.month - i
        while mo <= 0:
            mo += 12
            y -= 1
        key = f"{y:04d}-{mo:02d}"
        months.append(f"T{mo}")
        expenses.append(by_month.get(key, 0.0))
    return {"months": months, "expenses": expenses}


@app.get("/api/transactions")
def transactions(
    limit: int = 50,
    offset: int = 0,
    category: str | None = None,
    q: str | None = None,
    passcode: str = "",
):
    _check_passcode(passcode)
    user = _get_user_id()
    if not user:
        return {"data": [], "count": 0}
    sb = store.get_client()
    query = (
        sb.table("transactions")
        .select("id,amount,type,note,image_url,occurred_at,categories(id,name,emoji)")
        .eq("user_id", user["id"])
        .order("occurred_at", desc=True)
        .order("created_at", desc=True)
    )
    if category:
        query = query.eq("category_id", category)
    if q:
        query = query.ilike("note", f"%{q}%")
    res = query.range(offset, offset + limit - 1).execute()
    return {"data": res.data, "count": len(res.data)}


class TxBody(BaseModel):
    passcode: str
    amount: float
    type: str
    note: str = ""
    category_id: str | None = None
    occurred_at: str | None = None


@app.post("/api/transactions")
def add_transaction(body: TxBody):
    _check_passcode(body.passcode)
    user = _get_user_id()
    if not user:
        raise HTTPException(status_code=404, detail="No user")
    tx = store.save_transaction(
        user["id"], body.amount, body.type, body.note, body.category_id,
        occurred_at=body.occurred_at,
    )
    return tx


@app.delete("/api/transactions/{tx_id}")
def delete_transaction(tx_id: str, passcode: str = ""):
    _check_passcode(passcode)
    user = _get_user_id()
    if not user:
        raise HTTPException(status_code=404, detail="No user")
    store.delete_transaction(user["id"], tx_id)
    return {"ok": True}


@app.get("/api/categories")
def categories(passcode: str = ""):
    _check_passcode(passcode)
    user = _get_user_id()
    if not user:
        return {"data": []}
    return {"data": store.get_categories(user["id"])}


app.mount("/", StaticFiles(directory="web", html=True), name="web")
