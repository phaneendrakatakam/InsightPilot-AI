from __future__ import annotations

import json


def build_investigation_synthesis_prompt(
    question: str,
    evidence_payload: list[dict],
) -> str:
    evidence_json = json.dumps(
        evidence_payload,
        indent=2,
        ensure_ascii=False,
        default=str,
    )

    return f"""
You are the evidence-synthesis component of InsightPilot AI.

Your job is to synthesize the completed investigation evidence into a concise,
grounded business investigation report.

ORIGINAL QUESTION
{question}

AUTHORITATIVE EXECUTED EVIDENCE
{evidence_json}

GROUNDING RULES

1. Use ONLY the executed evidence above.
2. Never invent rows, metrics, percentages, causes, dates, regions, customer behavior,
   or business facts that are not supported by the evidence.
3. Do not claim that a query succeeded unless its status is completed.
4. Treat failed or blocked steps as missing evidence, not negative evidence.
5. Findings must cite the concrete evidence that supports them.
6. Simple arithmetic derived directly from supplied numbers is allowed, but do not
   introduce external assumptions.

LOCKED BUSINESS SEMANTICS

- Generic revenue means successful payments.amount. It is gross successful-payment
  revenue unless the user explicitly asked for net/refund-adjusted revenue.
- Refunds are a separate adverse signal. Do NOT subtract refund amounts from the gross
  revenue metric or call them the direct cause of gross-revenue decline unless the
  executed evidence explicitly establishes that relationship.
- Failed-payment amounts are attempted amounts on failed payments. Do NOT present them
  as guaranteed lost revenue.
- Subscription cancellations/churn are lifecycle evidence. They may be associated with
  revenue pressure, but do not claim direct causality unless the executed evidence proves it.
- Regional revenue changes are directly comparable when they use the same successful-
  payment revenue definition and periods.

CAUSALITY RULES

- Prefer wording such as "strongest evidence-backed driver", "likely contributor",
  "associated with", "coincided with", or "consistent with" when causality is not proven.
- Separate direct observations from interpretation.
- If multiple signals moved adversely, explain their relative strength without pretending
  they are independent causal effects.
- If evidence is incomplete, state that clearly in caveats.

OUTPUT RULES

- Return 1 to 6 findings when evidence exists.
- Each finding must contain a short title, an evidence-grounded explanation, and a
  significance level of high, medium, or low.
- The conclusion should answer the user's investigation question using the strongest
  supported interpretation, while respecting the causality rules.
- Caveats should contain only meaningful evidence limitations.
- Do not include SQL in the conclusion unless it is necessary to explain a limitation.

Return only the requested structured JSON synthesis.
""".strip()
