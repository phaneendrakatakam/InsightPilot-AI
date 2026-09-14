from app.core.governance import mask_sensitive_rows


def test_name_alias_is_pseudonymized_from_source_column():
    rows = [{"customer": "Customer 001"}]
    masked, fields = mask_sensitive_rows(
        rows,
        sql="SELECT customer_name AS customer FROM customers",
    )

    assert fields == ["customer"]
    assert masked[0]["customer"].startswith("Customer-")
    assert masked[0]["customer"] != "Customer 001"


def test_code_alias_uses_stable_code_token():
    rows = [{"account_ref": "CUST-0001"}]
    masked, fields = mask_sensitive_rows(
        rows,
        sql="SELECT customer_code AS account_ref FROM customers",
    )

    assert fields == ["account_ref"]
    assert masked[0]["account_ref"].startswith("Code-")


def test_email_alias_stays_fully_masked():
    rows = [{"contact": "person@example.com"}]
    masked, fields = mask_sensitive_rows(
        rows,
        sql="SELECT email AS contact FROM customers",
    )

    assert fields == ["contact"]
    assert masked[0]["contact"] == "[MASKED]"
