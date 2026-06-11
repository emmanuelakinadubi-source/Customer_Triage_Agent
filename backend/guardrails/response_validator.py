from dataclasses import dataclass

from .abuse_detector import detect_abuse
from .hallucination_checker import check_hallucinations


PROMISE_PHRASES = [
    "we will refund",
    "your refund is approved",
    "your issue is resolved",
    "guaranteed",
]

INTERNAL_DISCLOSURES = [
    "system prompt",
    "internal policy",
    "guardrail",
    "routing rule",
]


@dataclass(frozen=True)
class ResponseValidationResult:
    valid: bool
    reason: str = "Response is valid"


def validate_response(
    original_message: str,
    draft_response: str | None,
    abusive_flag: bool = False,
) -> ResponseValidationResult:
    if abusive_flag:
        if draft_response in (None, "FLAGGED - human review required"):
            return ResponseValidationResult(True)
        return ResponseValidationResult(False, "Abusive messages must not receive a customer draft")

    if not draft_response or not draft_response.strip():
        return ResponseValidationResult(False, "Draft response is required")

    abuse_result = detect_abuse(draft_response)
    if abuse_result.abusive:
        return ResponseValidationResult(False, "Draft response contains abusive language")

    lowered = draft_response.lower()
    for phrase in PROMISE_PHRASES:
        if phrase in lowered:
            return ResponseValidationResult(False, f"Draft response contains a promise: {phrase}")

    for phrase in INTERNAL_DISCLOSURES:
        if phrase in lowered and phrase not in (original_message or "").lower():
            return ResponseValidationResult(False, f"Draft response discloses internal detail: {phrase}")

    hallucination_result = check_hallucinations(original_message, draft_response)
    if not hallucination_result.valid:
        return ResponseValidationResult(False, hallucination_result.reason)

    return ResponseValidationResult(True)
