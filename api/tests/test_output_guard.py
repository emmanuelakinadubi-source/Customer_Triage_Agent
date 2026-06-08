"""
Tests for the output guard layer.

Section A — app/guards/routing_guard.py — guardrail_check() (low-level)
  The function has two execution paths:
  1. Fast deterministic path — returns early when draft is absent or
     routing/hallucination rules are violated, without calling the LLM.
  2. LLM path — calls client.beta.chat.completions.parse() when all
     deterministic checks pass.

Section B — app/guards/output_guard.py — check_output() (Pydantic interface)
  Verifies that check_output() correctly wraps guardrail_check() and returns
  a typed GuardrailResult Pydantic model.

Tests are grouped by the rule they exercise.
"""

import pytest
from unittest.mock import MagicMock

from app.guards.routing_guard import guardrail_check, GuardrailResult
from app.guards.output_guard import check_output, OutputGuardInput

# A clean draft that contains no fabricated values so it won't trigger
# the hallucination guard during deterministic checks.
CLEAN_DRAFT = "Thank you for contacting us. We will review your request shortly."


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_mock_client(valid: bool, reason: str = "All checks passed"):
    """Build a mock AzureOpenAI client whose .parse() returns a guardrail result."""
    mock_parsed = MagicMock()
    mock_parsed.model_dump.return_value = {"valid": valid, "reason": reason}
    mock_message = MagicMock()
    mock_message.parsed = mock_parsed
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    client = MagicMock()
    client.beta.chat.completions.parse.return_value = mock_response
    return client


# ---------------------------------------------------------------------------
# Skip logic — no draft present
# ---------------------------------------------------------------------------

class TestSkipLogic:
    def test_skip_when_draft_is_none(self):
        result = guardrail_check(
            "Refund Request", "Billing Team", "Low",
            None, "I want a refund", None, "test-model",
        )
        assert result["valid"] is True
        assert "Skipped" in result["reason"]

    def test_skip_when_draft_equals_not_mentioned(self):
        result = guardrail_check(
            "Refund Request", "Billing Team", "Low",
            "not mentioned", "I want a refund", None, "test-model",
        )
        assert result["valid"] is True
        assert "Skipped" in result["reason"]

    def test_skip_is_case_insensitive_for_not_mentioned(self):
        result = guardrail_check(
            "Refund Request", "Billing Team", "Low",
            "  Not Mentioned  ", "I want a refund", None, "test-model",
        )
        assert result["valid"] is True


# ---------------------------------------------------------------------------
# Routing rules — deterministic owner-to-category checks
# ---------------------------------------------------------------------------

class TestRoutingRules:
    def test_refund_request_to_logistics_is_invalid(self):
        result = guardrail_check(
            "Refund Request", "Logistics Team", "Low",
            CLEAN_DRAFT, "I want a refund", None, "test-model",
        )
        assert result["valid"] is False
        assert "Refund Request" in result["reason"]

    def test_delivery_issue_to_billing_is_invalid(self):
        result = guardrail_check(
            "Delivery Issue", "Billing Team", "Low",
            CLEAN_DRAFT, "Where is my order?", None, "test-model",
        )
        assert result["valid"] is False

    def test_product_complaint_to_logistics_is_invalid(self):
        result = guardrail_check(
            "Product Complaint", "Logistics Team", "Medium",
            CLEAN_DRAFT, "The product is broken.", None, "test-model",
        )
        assert result["valid"] is False

    def test_account_problem_to_logistics_is_invalid(self):
        result = guardrail_check(
            "Account Problem", "Logistics Team", "Low",
            CLEAN_DRAFT, "I cannot log in.", None, "test-model",
        )
        assert result["valid"] is False

    def test_unknown_category_fails(self):
        result = guardrail_check(
            "Made Up Category", "Billing Team", "Low",
            CLEAN_DRAFT, "Some message", None, "test-model",
        )
        assert result["valid"] is False
        assert "Unknown category" in result["reason"]

    def test_valid_routing_refund_to_billing_passes_deterministic(self):
        """Refund Request → Billing Team is valid; should proceed to LLM."""
        client = make_mock_client(valid=True)
        result = guardrail_check(
            "Refund Request", "Billing Team", "Low",
            CLEAN_DRAFT, "Please refund my order.",
            client, "test-model",
            urgency_reason="Customer requested a refund for a recent purchase.",
        )
        assert result["valid"] is True

    def test_valid_routing_delivery_to_logistics_passes_deterministic(self):
        client = make_mock_client(valid=True)
        result = guardrail_check(
            "Delivery Issue", "Logistics Team", "Medium",
            CLEAN_DRAFT, "My package has not arrived.",
            client, "test-model",
            urgency_reason="Customer reports a missing delivery after the expected date.",
        )
        assert result["valid"] is True


# ---------------------------------------------------------------------------
# High-urgency escalation rule
# ---------------------------------------------------------------------------

class TestHighUrgencyRule:
    def test_high_urgency_refund_without_escalation_fails(self):
        result = guardrail_check(
            "Refund Request", "Billing Team", "High",
            CLEAN_DRAFT, "URGENT: I need a refund immediately!", None, "test-model",
        )
        assert result["valid"] is False
        assert "Escalate to Manager" in result["reason"]

    def test_high_urgency_product_complaint_without_escalation_fails(self):
        result = guardrail_check(
            "Product Complaint", "Customer Service Agent", "High",
            CLEAN_DRAFT, "This product is dangerous!", None, "test-model",
        )
        assert result["valid"] is False

    def test_high_urgency_account_problem_without_escalation_fails(self):
        result = guardrail_check(
            "Account Problem", "Billing Team", "High",
            CLEAN_DRAFT, "My account has been compromised!", None, "test-model",
        )
        assert result["valid"] is False

    def test_high_urgency_delivery_issue_does_not_require_escalation(self):
        """Delivery Issue is NOT in the high-urgency escalation list."""
        client = make_mock_client(valid=True)
        result = guardrail_check(
            "Delivery Issue", "Logistics Team", "High",
            CLEAN_DRAFT, "My package is completely lost!",
            client, "test-model",
            urgency_reason="Customer reports the package has been missing for two weeks.",
        )
        assert result["valid"] is True

    def test_high_urgency_general_enquiry_does_not_require_escalation(self):
        client = make_mock_client(valid=True)
        result = guardrail_check(
            "General Enquiry", "Customer Service Agent", "High",
            CLEAN_DRAFT, "Can you help me urgently?",
            client, "test-model",
            urgency_reason="Customer marked this as urgent but the query is general.",
        )
        assert result["valid"] is True


# ---------------------------------------------------------------------------
# Hallucination guard — fabricated values in the draft response
# ---------------------------------------------------------------------------

class TestHallucinationGuard:
    def test_order_number_in_draft_not_in_message_fails(self):
        draft = "Your order #98765 has been cancelled."
        result = guardrail_check(
            "Refund Request", "Billing Team", "Low",
            draft, "I want a refund", None, "test-model",
        )
        assert result["valid"] is False
        assert "Hallucinated value" in result["reason"]

    def test_ord_reference_in_draft_not_in_message_fails(self):
        draft = "We are reviewing order ORD-55555 for you."
        result = guardrail_check(
            "Delivery Issue", "Logistics Team", "Low",
            draft, "Where is my package?", None, "test-model",
        )
        assert result["valid"] is False

    def test_dollar_amount_in_draft_not_in_message_fails(self):
        draft = "We will refund you $49.99 within 5 days."
        result = guardrail_check(
            "Refund Request", "Billing Team", "Low",
            draft, "I want a refund", None, "test-model",
        )
        assert result["valid"] is False
        assert "Hallucinated value" in result["reason"]

    def test_pound_amount_in_draft_not_in_message_fails(self):
        draft = "Your refund of £29.99 is being processed."
        result = guardrail_check(
            "Refund Request", "Billing Team", "Low",
            draft, "I want a refund", None, "test-model",
        )
        assert result["valid"] is False

    def test_euro_amount_in_draft_not_in_message_fails(self):
        draft = "We will process your €15.00 refund."
        result = guardrail_check(
            "Refund Request", "Billing Team", "Low",
            draft, "I want a refund", None, "test-model",
        )
        assert result["valid"] is False

    def test_value_present_in_original_message_is_not_flagged(self):
        """A value that appears verbatim in the original message must not be flagged."""
        message = "My order #12345 has not arrived."
        draft = "We are looking into order #12345 for you."
        client = make_mock_client(valid=True)
        result = guardrail_check(
            "Delivery Issue", "Logistics Team", "Low",
            draft, message, client, "test-model",
            urgency_reason="Customer reports the order did not arrive as expected.",
        )
        assert result["valid"] is True


# ---------------------------------------------------------------------------
# LLM guardrail path
# ---------------------------------------------------------------------------

class TestLLMGuardrail:
    def test_llm_valid_result_is_returned(self):
        client = make_mock_client(valid=True, reason="All checks passed")
        result = guardrail_check(
            "General Enquiry", "Customer Service Agent", "Low",
            CLEAN_DRAFT, "What are your opening hours?",
            client, "test-model",
            urgency_reason="Customer asked a general question about business hours.",
        )
        assert result["valid"] is True
        assert result["reason"] == "All checks passed"
        client.beta.chat.completions.parse.assert_called_once()

    def test_llm_invalid_result_is_returned(self):
        client = make_mock_client(valid=False, reason="FAIL_ROUTING")
        result = guardrail_check(
            "General Enquiry", "Customer Service Agent", "Low",
            CLEAN_DRAFT, "What are your opening hours?",
            client, "test-model",
            urgency_reason="Customer asked a general question about business hours.",
        )
        assert result["valid"] is False
        assert result["reason"] == "FAIL_ROUTING"

    def test_llm_exception_returns_invalid_with_error_message(self):
        client = MagicMock()
        client.beta.chat.completions.parse.side_effect = Exception("Connection timeout")
        result = guardrail_check(
            "General Enquiry", "Customer Service Agent", "Low",
            CLEAN_DRAFT, "What are your opening hours?",
            client, "test-model",
            urgency_reason="Customer asked a general question about business hours.",
        )
        assert result["valid"] is False
        assert "Guardrail API execution error" in result["reason"]
        assert "Connection timeout" in result["reason"]


# ---------------------------------------------------------------------------
# Section B — check_output() Pydantic interface (output_guard.py)
# ---------------------------------------------------------------------------

class TestCheckOutput:
    """Verify that check_output() correctly wraps guardrail_check() and
    returns a strongly-typed GuardrailResult Pydantic model."""

    def _build_input(self, **overrides) -> OutputGuardInput:
        defaults = dict(
            category="General Enquiry",
            suggested_owner="Customer Service Agent",
            urgency="Low",
            draft_response=CLEAN_DRAFT,
            original_message="What are your opening hours?",
            urgency_reason="Customer asked a general question about business hours.",
        )
        defaults.update(overrides)
        return OutputGuardInput(**defaults)

    def test_returns_guardrail_result_pydantic_model(self):
        client = make_mock_client(valid=True)
        result = check_output(self._build_input(), client, "test-model")
        assert isinstance(result, GuardrailResult)

    def test_valid_result_propagated(self):
        client = make_mock_client(valid=True, reason="All checks passed")
        result = check_output(self._build_input(), client, "test-model")
        assert result.valid is True
        assert result.reason == "All checks passed"

    def test_invalid_result_propagated(self):
        client = make_mock_client(valid=False, reason="FAIL_ROUTING")
        result = check_output(self._build_input(), client, "test-model")
        assert result.valid is False
        assert result.reason == "FAIL_ROUTING"

    def test_deterministic_failure_returned_without_llm_call(self):
        """Routing violation is caught before the LLM is called."""
        client = MagicMock()
        result = check_output(
            self._build_input(
                category="Refund Request",
                suggested_owner="Logistics Team",  # wrong owner
            ),
            client,
            "test-model",
        )
        assert result.valid is False
        client.beta.chat.completions.parse.assert_not_called()

    def test_no_draft_is_skipped(self):
        client = MagicMock()
        result = check_output(
            self._build_input(draft_response=None),
            client,
            "test-model",
        )
        assert result.valid is True
        assert "Skipped" in result.reason
        client.beta.chat.completions.parse.assert_not_called()

    def test_output_guard_input_rejects_missing_required_fields(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            OutputGuardInput(
                category="General Enquiry",
                # missing suggested_owner, urgency, draft_response, original_message
            )
