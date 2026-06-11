import re


RETURN_POLICY_TERMS = re.compile(
    r"\b(refund|refunds|return|returns|returned|returning|exchange|exchanges)\b",
    flags=re.IGNORECASE,
)
NUMBER_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
}
OUTSIDE_WINDOW_PATTERNS = [
    re.compile(r"\b(?:over|more than|longer than)\s+30\s+days?\b", re.IGNORECASE),
    re.compile(r"\b(?:after|past|outside)\s+(?:the\s+)?30[-\s]?day\b", re.IGNORECASE),
    re.compile(r"\b(?:1|one)\s+months?\s+ago\b", re.IGNORECASE),
    re.compile(r"\b\d+\s+months?\s+ago\b", re.IGNORECASE),
]
DAYS_AGO_PATTERN = re.compile(r"\b(\d+)\s+days?\s+ago\b", re.IGNORECASE)
WORD_MONTHS_AGO_PATTERN = re.compile(
    rf"\b({'|'.join(NUMBER_WORDS)})\s+months?\s+ago\b",
    flags=re.IGNORECASE,
)
NON_RETURNABLE_PATTERNS = [
    re.compile(r"\bgift\s+cards?\b", re.IGNORECASE),
    re.compile(r"\bdownloadable\s+software\s+products?\b", re.IGNORECASE),
    re.compile(r"\b(?:custom[-\s]?made|personalized)\s+items?\b", re.IGNORECASE),
]


OUTSIDE_RETURN_WINDOW_RESPONSE = (
    "Thank you for contacting us. Our return policy allows returns within 30 days "
    "from the date of delivery only. Since your order was received more than 30 "
    "days ago, it is outside the return policy timeframe."
)
NON_RETURNABLE_ITEM_RESPONSE = (
    "Thank you for contacting us. According to our return policy, gift cards, "
    "downloadable software products, and custom-made or personalized items are "
    "non-returnable. Because your request is for a gift card, it cannot be returned "
    "under the return policy."
)


def is_return_policy_request(message: str) -> bool:
    return bool(RETURN_POLICY_TERMS.search(message))


def is_outside_return_window(message: str) -> bool:
    if not is_return_policy_request(message):
        return False

    if any(pattern.search(message) for pattern in OUTSIDE_WINDOW_PATTERNS):
        return True

    days_match = DAYS_AGO_PATTERN.search(message)
    if days_match and int(days_match.group(1)) > 30:
        return True

    word_months_match = WORD_MONTHS_AGO_PATTERN.search(message)
    if word_months_match and NUMBER_WORDS[word_months_match.group(1).lower()] >= 1:
        return True

    return False


def is_non_returnable_item_request(message: str) -> bool:
    if not is_return_policy_request(message):
        return False

    return any(pattern.search(message) for pattern in NON_RETURNABLE_PATTERNS)


def apply_return_policy_guard(message: str, triage_output: dict) -> dict:
    if is_non_returnable_item_request(message):
        guarded_output = dict(triage_output)
        guarded_output["category"] = "Refund Request"
        guarded_output["suggested_owner"] = "Customer Service Agent"
        guarded_output["draft_response"] = NON_RETURNABLE_ITEM_RESPONSE
        guarded_output["urgency_reason"] = "Customer requested return of a non-returnable policy item."
        return guarded_output

    if not is_outside_return_window(message):
        return triage_output

    guarded_output = dict(triage_output)
    guarded_output["category"] = "Refund Request"
    guarded_output["suggested_owner"] = "Customer Service Agent"
    guarded_output["draft_response"] = OUTSIDE_RETURN_WINDOW_RESPONSE
    guarded_output["urgency_reason"] = "Customer is outside the stated return policy window."
    return guarded_output
