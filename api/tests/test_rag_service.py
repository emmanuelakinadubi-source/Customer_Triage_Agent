from pathlib import Path

from app.prompts.system_prompt import build_user_message
from app.services.rag_service import PolicyRAGService


def test_policy_rag_retrieves_relevant_refund_sections(tmp_path):
    policy_file = tmp_path / "policy.txt"
    policy_file.write_text(
        """# Return and Refund Policy

## 1. Timeframe
Customers have 30 days from delivery to request a return.

## 2. Refund Process
Approved refunds are processed within 7-10 business days.

## 3. Shipping Costs
Shipping costs are non-refundable.
""",
        encoding="utf-8",
    )

    service = PolicyRAGService(document_path=str(policy_file), top_k=2)
    context = service.build_context("How long does my refund take?")

    assert "Refund Process" in context
    assert "7-10 business days" in context


def test_policy_rag_always_includes_timeframe_for_refund_requests(tmp_path):
    policy_file = tmp_path / "policy.txt"
    policy_file.write_text(
        """# Return and Refund Policy

## 1. Timeframe
Customers have 30 days from delivery to request a return.

## 2. Refund Process
Approved refunds are processed within 7-10 business days.
""",
        encoding="utf-8",
    )

    service = PolicyRAGService(document_path=str(policy_file), top_k=1)
    context = service.build_context("I want a refund for my order.")

    assert "Timeframe" in context
    assert "30 days from delivery" in context


def test_triage_prompt_includes_retrieved_policy_context():
    prompt = build_user_message(
        "Can I return my order?",
        "Section: 1. Timeframe\nCustomers have 30 days from delivery.",
    )

    assert "Relevant policy context retrieved from the knowledge base" in prompt
    assert "Customers have 30 days from delivery" in prompt
