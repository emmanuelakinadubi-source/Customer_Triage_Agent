from app.guards.return_policy_guard import (
    NON_RETURNABLE_ITEM_RESPONSE,
    NON_RETURNABLE_SOFTWARE_RESPONSE,
    OUTSIDE_RETURN_WINDOW_RESPONSE,
    apply_return_policy_guard,
    is_non_returnable_item_request,
    is_outside_return_window,
)


def test_detects_return_request_received_two_months_ago():
    assert is_outside_return_window(
        "I want to return my order. I received it two months ago."
    )


def test_detects_exact_three_month_return_message():
    assert is_outside_return_window(
        "i recieved my package 3 months ago it was really good but now i kinda dont like it and want to return it"
    )


def test_detects_refund_request_over_30_days():
    assert is_outside_return_window(
        "I need a refund, but it has been 45 days ago since delivery."
    )


def test_does_not_trigger_without_return_policy_terms():
    assert not is_outside_return_window(
        "My package arrived two months ago and I have a question."
    )


def test_detects_gift_card_return_as_non_returnable():
    assert is_non_returnable_item_request(
        "i ordered a amazon gift card which i recieved yesterday but i want to return it"
    )


def test_detects_one_word_giftcard_return_as_non_returnable():
    assert is_non_returnable_item_request(
        "received my giftcard 2 days ago but havent used it and want to return it now"
    )


def test_detects_software_return_as_non_returnable():
    assert is_non_returnable_item_request(
        "I bought software yesterday and want to return it for a refund."
    )


def test_uses_latest_message_intent_with_conversation_context():
    message = '''Conversation context for reference only:
"""
Customer: I ordered an amazon gift card yesterday.
Assistant draft (General Enquiry, Customer Service Agent): Gift cards are non-returnable.
"""

Latest customer message to triage:
"""
I want to return it now.
"""
'''

    assert is_non_returnable_item_request(message)


def test_old_return_context_does_not_trigger_unrelated_latest_message():
    message = '''Conversation context for reference only:
"""
Customer: I ordered an amazon gift card yesterday and want to return it.
Assistant draft (Refund Request, Customer Service Agent): Gift cards are non-returnable.
"""

Latest customer message to triage:
"""
Where is my package?
"""
'''

    assert not is_non_returnable_item_request(message)


def test_overrides_llm_draft_for_non_returnable_gift_card():
    llm_output = {
        "category": "Refund Request",
        "urgency": "Low",
        "urgency_reason": "Customer wants to return a gift card.",
        "sentiment": "Neutral",
        "suggested_owner": "Billing Team",
        "draft_response": "Please provide the delivery date so we can check eligibility.",
        "confidence": "High",
        "abusive_flag": False,
    }

    guarded_output = apply_return_policy_guard(
        "i ordered a amazon gift card which i recieved yesterday but i want to return it",
        llm_output,
    )

    assert guarded_output["draft_response"] == NON_RETURNABLE_ITEM_RESPONSE
    assert "gift card" in guarded_output["draft_response"]
    assert "non-returnable" in guarded_output["draft_response"]
    assert "support team" not in guarded_output["draft_response"]


def test_overrides_llm_draft_for_non_returnable_software():
    llm_output = {
        "category": "Refund Request",
        "urgency": "Low",
        "urgency_reason": "Customer wants to return software.",
        "sentiment": "Neutral",
        "suggested_owner": "Billing Team",
        "draft_response": "Please provide the delivery date so we can check eligibility.",
        "confidence": "High",
        "abusive_flag": False,
    }

    guarded_output = apply_return_policy_guard(
        "I bought software yesterday and want to return it for a refund.",
        llm_output,
    )

    assert guarded_output["draft_response"] == NON_RETURNABLE_SOFTWARE_RESPONSE
    assert "downloadable software product" in guarded_output["draft_response"]
    assert "non-returnable" in guarded_output["draft_response"]
    assert "delivery date" not in guarded_output["draft_response"]


def test_overrides_llm_draft_for_outside_return_window():
    llm_output = {
        "category": "Refund Request",
        "urgency": "Low",
        "urgency_reason": "Customer wants to return an order.",
        "sentiment": "Neutral",
        "suggested_owner": "Billing Team",
        "draft_response": "We will assist you with the return process.",
        "confidence": "High",
        "abusive_flag": False,
    }

    guarded_output = apply_return_policy_guard(
        "I want to return my order received two months ago.",
        llm_output,
    )

    assert guarded_output["draft_response"] == OUTSIDE_RETURN_WINDOW_RESPONSE
    assert "within 30 days" in guarded_output["draft_response"]
    assert "outside the return policy timeframe" in guarded_output["draft_response"]
    assert "support team" not in guarded_output["draft_response"]
