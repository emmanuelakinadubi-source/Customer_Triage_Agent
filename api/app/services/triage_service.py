from typing import Dict

from ..utils.text_cleaning import clean_text


def triage_message(message: str) -> Dict[str, object]:
    normalized = clean_text(message)
    if not normalized:
        return {
            "category": "Unspecified",
            "urgency": "Low",
            "urgency_reason": "The message could not be classified.",
            "sentiment": "Neutral",
            "suggested_owner": "Customer Service Agent",
            "draft_response": "Thank you for your message. We are reviewing it now.",
            "confidence": "Low",
            "abusive_flag": False,
            "validation_status": "failed_validation",
        }

    return {
        "category": "General Enquiry",
        "urgency": "Low",
        "urgency_reason": "The message is a general request and does not indicate an immediate issue.",
        "sentiment": "Neutral",
        "suggested_owner": "Customer Service Agent",
        "draft_response": "Thank you for reaching out. We have received your message and will review it shortly.",
        "confidence": "Medium",
        "abusive_flag": False,
        "validation_status": "pending_implementation",
    }
