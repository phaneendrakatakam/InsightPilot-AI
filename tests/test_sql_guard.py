import pytest

from app.core.sql_guard import SqlValidationError, validate_sql


def test_select_is_allowed_and_limited():
    result = validate_sql("SELECT customer_id, customer_name FROM customers")

    assert result.tables == ["customers"]
    assert "LIMIT 500" in result.executable_sql.upper()


def test_with_select_is_allowed():
    result = validate_sql(
        """
        WITH successful AS (
            SELECT customer_id, amount
            FROM payments
            WHERE payment_status = 'SUCCESS'
        )
        SELECT customer_id, SUM(amount) AS revenue
        FROM successful
        GROUP BY customer_id
        ORDER BY revenue DESC
        LIMIT 5
        """
    )

    assert result.tables == ["payments"]
    assert "LIMIT 5" in result.executable_sql.upper()


@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM customers WHERE customer_id = 1",
        "UPDATE customers SET account_status = 'CLOSED' WHERE customer_id = 1",
        "INSERT INTO regions(region_code, region_name) VALUES ('X', 'X')",
        "DROP TABLE customers",
        "ALTER TABLE customers ADD COLUMN unsafe text",
        "CREATE TABLE unsafe(id int)",
    ],
)
def test_write_and_ddl_are_blocked(sql):
    with pytest.raises(SqlValidationError):
        validate_sql(sql)


def test_multiple_statements_are_blocked():
    with pytest.raises(SqlValidationError):
        validate_sql("SELECT * FROM customers; SELECT * FROM payments;")


def test_unapproved_table_is_blocked():
    with pytest.raises(SqlValidationError):
        validate_sql("SELECT * FROM pg_catalog.pg_user")


def test_unknown_application_table_is_blocked():
    with pytest.raises(SqlValidationError):
        validate_sql("SELECT * FROM secret_table")


def test_large_limit_is_capped_at_500():
    result = validate_sql("SELECT * FROM payments LIMIT 5000")

    assert "LIMIT 500" in result.executable_sql.upper()
    assert "LIMIT 5000" not in result.executable_sql.upper()


def test_small_limit_is_preserved():
    result = validate_sql("SELECT * FROM payments LIMIT 25")

    assert "LIMIT 25" in result.executable_sql.upper()


def test_limit_all_is_safely_capped_at_500():
    # PostgreSQL LIMIT ALL is equivalent to having no LIMIT.
    # sqlglot normalizes it away, after which InsightPilot's guard
    # applies the mandatory V1 maximum result limit of 500 rows.
    result = validate_sql("SELECT * FROM payments LIMIT ALL")

    assert "LIMIT 500" in result.executable_sql.upper()


def test_dangerous_function_is_blocked():
    with pytest.raises(SqlValidationError):
        validate_sql("SELECT pg_sleep(20)")


def test_cte_name_is_not_treated_as_unapproved_table():
    result = validate_sql(
        """
        WITH recent_payments AS (
            SELECT customer_id, amount
            FROM payments
        )
        SELECT * FROM recent_payments
        """
    )

    assert result.tables == ["payments"]
