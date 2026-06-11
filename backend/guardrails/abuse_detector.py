import re
from dataclasses import dataclass


ABUSE_PATTERNS = [
    r"\bidiot\b",
    r"\bstupid\b",
    r"\bdumb\b",
    r"\bshut\s+up\b",
    r"\bworthless\b",
    r"\btrash\b",
    r"\bscam(?:mer|ming)?\b",
]


@dataclass(frozen=True)
class AbuseDetectionResult:
    abusive: bool
    reason: str = "No abusive language detected"


def detect_abuse(message: str) -> AbuseDetectionResult:
    text = message or ""
    for pattern in ABUSE_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            return AbuseDetectionResult(True, "Potential abusive language detected")

    return AbuseDetectionResult(False)
