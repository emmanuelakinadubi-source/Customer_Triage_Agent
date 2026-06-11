from backend.guardrails.abuse_detector import detect_abuse


def test_detects_abusive_language():
    result = detect_abuse("Your service is stupid and worthless.")

    assert result.abusive is True


def test_allows_normal_customer_message():
    result = detect_abuse("I need help with my delivery.")

    assert result.abusive is False
