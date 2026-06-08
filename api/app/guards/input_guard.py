import re
from pydantic import BaseModel

MAX_MESSAGE_LENGTH = 5_000

# Patterns that indicate an attempt to override or hijack the triage system.
# Checked deterministically before any LLM call is made.
_INJECTION_PATTERNS = [
    r"ignore\s+(previous|all|above)\s+instructions?",
    r"you\s+are\s+now\s+a",
    r"disregard\s+(your|the)\s+system\s+(prompt|message)",
    r"new\s+instructions?\s*:",
    r"repeat\s+your\s+instructions?",
    r"what\s+is\s+your\s+(prompt|system\s+message)",
    r"print\s+your\s+system\s+",
    r"act\s+as\s+(?:an?\s+)?(?:ai|llm|assistant|model|bot|gpt)",
]


class InputGuardResult(BaseModel):
    valid: bool
    cleaned_message: str = ""
    reason: str = ""


def check_input(message: str) -> InputGuardResult:
    cleaned = message.strip()

    if not cleaned:
        return InputGuardResult(
            valid=False,
            cleaned_message=cleaned,
            reason="Message is empty",
        )

    if len(cleaned) > MAX_MESSAGE_LENGTH:
        return InputGuardResult(
            valid=False,
            cleaned_message=cleaned,
            reason=f"Message exceeds the {MAX_MESSAGE_LENGTH:,}-character limit",
        )

    for pattern in _INJECTION_PATTERNS:
        if re.search(pattern, cleaned, re.IGNORECASE):
            return InputGuardResult(
                valid=False,
                cleaned_message=cleaned,
                reason="Potential prompt injection attempt detected",
            )

    return InputGuardResult(valid=True, cleaned_message=cleaned)
