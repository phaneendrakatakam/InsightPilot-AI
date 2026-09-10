from app.prompts.answer_generation import build_answer_generation_prompt


def _prompt():
    return build_answer_generation_prompt(
        question="Which region generated the most revenue in August 2026?",
        executed_sql=(
            "SELECT r.region_name, SUM(p.amount) AS revenue "
            "FROM payments p JOIN customers c ON p.customer_id=c.customer_id "
            "JOIN regions r ON c.region_id=r.region_id "
            "WHERE p.payment_status='SUCCESS' "
            "GROUP BY r.region_name ORDER BY revenue DESC LIMIT 1"
        ),
        columns=["region_name", "revenue"],
        rows=[{"region_name": "North", "revenue": 493803}],
        row_count=1,
    )


def test_answer_prompt_locks_currency_to_inr():
    prompt = _prompt()
    assert "Indian Rupees (INR)" in prompt
    assert "use ₹ or INR" in prompt
    assert "Never substitute $, €, £" in prompt


def test_answer_prompt_forbids_currency_invention():
    prompt = _prompt()
    assert "Never invent a metric" in prompt
    assert "currency" in prompt


def test_answer_prompt_forbids_metric_substitution():
    prompt = _prompt()
    assert 'Do not replace "revenue" with "sales volume"' in prompt


def test_answer_prompt_forbids_causal_inference_from_rankings():
    prompt = _prompt()
    assert "Do not infer causes from ranking or aggregate queries." in prompt
