import re
from dataclasses import dataclass


VALUE_PATTERNS = [
    r"#\d+",
    r"\bORD[- ]?\d+\b",
    r"\b[A-Z]{2,}[- ]?\d{3,}\b",
    r"[$£€]\s?\d+(?:\.\d{2})?",
    r"\b\d+\s?(?:business\s+)?days?\b",
]

ALLOWED_POLICY_VALUES = {"30 days", "30-day"}


@dataclass(frozen=True)
class HallucinationResult:
    valid: bool
    reason: str = "No hallucinated values detected"
    hallucinated_values: tuple[str, ...] = ()


def check_hallucinations(original_message: str, draft_response: str | None) -> HallucinationResult:
    if not draft_response:
        return HallucinationResult(True)

    source = original_message or ""
    found: list[str] = []

    for pattern in VALUE_PATTERNS:
        for match in re.findall(pattern, draft_response, flags=re.IGNORECASE):
            value = match.strip()
            if value.lower() in ALLOWED_POLICY_VALUES:
                continue
            if value not in source:
                found.append(value)

    unique_values = tuple(dict.fromkeys(found))
    if unique_values:
        return HallucinationResult(
            False,
            f"Hallucinated values detected: {', '.join(unique_values)}",
            unique_values,
        )

    return HallucinationResult(True)
