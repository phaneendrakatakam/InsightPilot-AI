from app.schemas.conversation import ConversationContext
from app.services.context_manager import update_conversation_context
from app.services.intent_router import classify_intent

def route(message: str, previous=None):
    previous = previous or ConversationContext()
    resolved = update_conversation_context(previous, message)
    return classify_intent(message, previous, resolved), resolved

def test_investigation():
    decision, _ = route("Why did revenue decline in August compared with July?")
    assert decision.intent == "investigation"

def test_comparison():
    previous = ConversationContext(metric="revenue", primary_period="August", comparison_period="July", revision=1)
    decision, _ = route("Compare South with North.", previous)
    assert decision.intent == "comparison"
    assert decision.uses_prior_context is True

def test_drill_down():
    previous = ConversationContext(metric="revenue", primary_period="August", comparison_period="July", revision=1)
    decision, resolved = route("Investigate South.", previous)
    assert decision.intent == "drill_down"
    assert resolved.region == "South"

def test_follow_up():
    previous = ConversationContext(metric="revenue", primary_period="August", comparison_period="July", revision=2)
    decision, resolved = route("What about refunds?", previous)
    assert decision.intent == "follow_up"
    assert resolved.metric == "refunds"

def test_explanation():
    decision, _ = route("Explain this result.", ConversationContext(revision=2))
    assert decision.intent == "explanation"

def test_challenge():
    decision, _ = route("Are you sure payment failures actually caused it?", ConversationContext(revision=3))
    assert decision.intent == "challenge"

def test_evidence_request():
    decision, _ = route("Show me the SQL behind that.", ConversationContext(revision=3))
    assert decision.intent == "evidence_request"

def test_simple_query():
    decision, resolved = route("What was August revenue?")
    assert decision.intent == "simple_query"
    assert resolved.metric == "revenue"
    assert resolved.primary_period == "August"
