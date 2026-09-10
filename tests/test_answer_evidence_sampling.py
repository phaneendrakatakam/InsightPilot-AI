from app.prompts.answer_generation import (
    MODEL_EVIDENCE_SAMPLE_LIMIT,
    build_answer_generation_prompt,
)


def test_prompt_distinguishes_query_rows_from_model_sample():
    rows = [{"customer_id": i} for i in range(101)]

    prompt = build_answer_generation_prompt(
        question="Show customers with failed payments in August 2026.",
        executed_sql=(
            "SELECT DISTINCT c.customer_id "
            "FROM customers c JOIN payments p ON c.customer_id=p.customer_id "
            "WHERE p.payment_status='FAILED'"
        ),
        columns=["customer_id"],
        rows=rows,
        row_count=101,
    )

    assert MODEL_EVIDENCE_SAMPLE_LIMIT == 100
    assert '"query_row_count": 101' in prompt
    assert '"model_sample_row_count": 100' in prompt


def test_prompt_forbids_display_wording_from_model_sample():
    prompt = build_answer_generation_prompt(
        question="Show customers with failed payments.",
        executed_sql="SELECT DISTINCT customer_id FROM payments",
        columns=["customer_id"],
        rows=[{"customer_id": 1}, {"customer_id": 2}],
        row_count=2,
    )

    assert 'Never say that only the model sample is "displayed"' in prompt
    assert "Do not create a caveat merely because" in prompt
