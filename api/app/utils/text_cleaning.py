import re


def clean_text(text: str) -> str:
    normalized = text.strip()
    normalized = re.sub(r"\s+", " ", normalized)
    normalized = re.sub(r"[\r\n]+", " ", normalized)
    return normalized
