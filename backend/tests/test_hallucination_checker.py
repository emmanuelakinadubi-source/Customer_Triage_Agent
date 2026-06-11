from backend.guardrails.hallucination_checker import check_hallucinations


def test_allows_values_present_in_original_message():
    result = check_hallucinations(
        "My order #1234 has not arrived.",
        "Thanks for contacting us about order #1234.",
    )

    assert result.valid is True


def test_rejects_new_order_number_in_draft():
    result = check_hallucinations(
        "My package has not arrived.",
        "Thanks for contacting us about order #9876.",
    )

    assert result.valid is False
    assert "#9876" in result.hallucinated_values


def test_allows_approved_return_policy_window():
    result = check_hallucinations(
        "Can I return this?",
        "Returns are accepted within 30 days of purchase.",
    )

    assert result.valid is True
