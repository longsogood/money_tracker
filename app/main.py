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


@app.get("/api/summary")
def summary(year: int | None = None, month: int | None = None, passcode: str = ""):
    _check_passcode(passcode)
    telegram_id = None  # dashboard dùng user đầu tiên — dự án cá nhân 1 người
    sb = store.get_client()
    user = sb.table("users").select("id").limit(1).execute()
    if not user.data:
        return {"total_expense": 0, "total_income": 0, "by_category": [], "transactions": [], "expense_count": 0, "income_count": 0}
    user_id = user.data[0]["id"]
    today = dt.date.today()
    return store.get_month_summary(
        user_id, year or today.year, month or today.month
    )


@app.get("/api/transactions")
def transactions(limit: int = 50, offset: int = 0, passcode: str = ""):
    _check_passcode(passcode)
    sb = store.get_client()
    user = sb.table("users").select("id").limit(1).execute()
    if not user.data:
        return {"data": [], "count": 0}
    user_id = user.data[0]["id"]
    res = (
        sb.table("transactions")
        .select("id,amount,type,note,image_url,occurred_at,categories(name,emoji)")
        .eq("user_id", user_id)
        .order("occurred_at", desc=True)
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )
    return {"data": res.data, "count": len(res.data)}


app.mount("/", StaticFiles(directory="web", html=True), name="web")
