from typing import Optional
from pydantic import BaseModel
from app.guards.routing_guard import guardrail_check, GuardrailResult


class OutputGuardInput(BaseModel):
    """Typed input for the output guard — built from the LLM's raw triage result."""
    category: str
    suggested_owner: str
    urgency: str
    draft_response: Optional[str]
    original_message: str
    urgency_reason: Optional[str] = None
    sentiment: str = "Neutral"
    confidence: str = "Medium"
    abusive_flag: bool = False


def check_output(guard_input: OutputGuardInput, client, deployment: str) -> GuardrailResult:
    """Validate triage output against business rules and the LLM guardrail.

    Returns a GuardrailResult with valid=True when all checks pass.
    """
    result = guardrail_check(
        category=guard_input.category,
        owner=guard_input.suggested_owner,
        urgency=guard_input.urgency,
        draft_response=guard_input.draft_response,
        original_message=guard_input.original_message,
        client=client,
        deployment=deployment,
        urgency_reason=guard_input.urgency_reason,
        sentiment=guard_input.sentiment,
        confidence=guard_input.confidence,
        abusive_flag=guard_input.abusive_flag,
    )
    return GuardrailResult(**result)
