from app.parser import parse_message


def test_simple_k():
    r = parse_message("50k ăn trưa")
    assert r["amount"] == 50000
    assert r["note"] == "ăn trưa"
    assert r["is_income"] is False


def test_tr():
    r = parse_message("1tr tiền điện")
    assert r["amount"] == 1000000
    assert r["note"] == "tiền điện"


def test_plain_number():
    r = parse_message("50000 xăng xe")
    assert r["amount"] == 50000
    assert r["note"] == "xăng xe"


def test_income_prefix():
    r = parse_message("+15tr lương")
    assert r["amount"] == 15000000
    assert r["is_income"] is True


def test_income_keyword():
    r = parse_message("thu 500k")
    assert r["amount"] == 500000
    assert r["is_income"] is True


def test_no_amount():
    assert parse_message("ăn trưa nhé") is None


def test_amount_only():
    r = parse_message("50k")
    assert r["amount"] == 50000
    assert r["note"] == ""
