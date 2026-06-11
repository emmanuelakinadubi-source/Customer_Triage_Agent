from backend.guardrails.response_validator import validate_response


def test_accepts_safe_response():
    result = validate_response(
        "My order #1234 is late.",
        "Thanks for contacting us about order #1234. Our team can help check this.",
    )

    assert result.valid is True


def test_rejects_empty_response_for_non_abusive_message():
    result = validate_response("Where is my parcel?", "")

    assert result.valid is False
    assert "required" in result.reason


def test_rejects_promised_refund():
    result = validate_response(
        "I want a refund.",
        "We will refund you today.",
    )

    assert result.valid is False
    assert "promise" in result.reason


def test_rejects_abusive_message_with_customer_draft():
    result = validate_response(
        "You are stupid.",
        "I can help with that.",
        abusive_flag=True,
    )

    assert result.valid is False


def test_accepts_abusive_message_human_review_placeholder():
    result = validate_response(
        "You are stupid.",
        "FLAGGED - human review required",
        abusive_flag=True,
    )

    assert result.valid is True
