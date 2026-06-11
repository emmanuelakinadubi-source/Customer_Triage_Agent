from backend.guardrails.owner_validator import validate_owner


def test_validates_allowed_owner_for_refund_request():
    result = validate_owner("Refund Request", "Billing Team")

    assert result.valid is True


def test_rejects_owner_that_does_not_match_category():
    result = validate_owner("Delivery Issue", "Billing Team")

    assert result.valid is False
    assert "Delivery Issue" in result.reason


def test_high_urgency_refund_request_requires_manager():
    result = validate_owner("Refund Request", "Billing Team", urgency="High")

    assert result.valid is False
    assert "Escalate to Manager" in result.reason


def test_rejects_unknown_category():
    result = validate_owner("Unknown", "Customer Service Agent")

    assert result.valid is False
    assert "Unknown category" in result.reason
