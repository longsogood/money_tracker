"""Parse tin nhắn tiếng Việt kiểu '50k ăn trưa', '-50000 xăng', 'thu 15tr lương'."""
import re

AMOUNT_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*(k|tr|m|ng|nghìn|trieu|triệu)?", re.IGNORECASE)

MULTIPLIERS = {
    None: 1,
    "k": 1_000,
    "ng": 1_000,
    "nghìn": 1_000,
    "tr": 1_000_000,
    "m": 1_000_000,
    "trieu": 1_000_000,
    "triệu": 1_000_000,
}

INCOME_KEYWORDS = ("thu", "lương", "nhận", "income", "thưởng", "bonus")


def _normalize_number(raw: str) -> float:
    return float(raw.replace(",", "."))


def parse_message(text: str) -> dict | None:
    """Trả về {'amount': float, 'is_income': bool, 'note': str} hoặc None nếu không parse được."""
    text = text.strip()
    if not text:
        return None

    is_income = text.startswith("+") or any(
        text.lower().startswith(k) for k in INCOME_KEYWORDS
    )

    match = AMOUNT_RE.search(text)
    if not match:
        return None

    value = _normalize_number(match.group(1))
    unit = match.group(2)
    if unit:
        unit = unit.lower()
    mult = MULTIPLIERS.get(unit, 1)
    amount = value * mult

    # note = phần text bỏ số tiền, dấu +/-
    note = AMOUNT_RE.sub("", text, count=1)
    note = note.strip(" -+.,:;")
    if not note:
        note = ""

    return {"amount": amount, "is_income": is_income, "note": note}
