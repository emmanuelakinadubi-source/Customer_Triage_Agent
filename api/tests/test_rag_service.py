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


def test_policy_rag_includes_non_returnable_section_for_software_refunds(tmp_path):
    policy_file = tmp_path / "refund_policy.txt"
    policy_file.write_text(
        """# Return and Refund Policy

## 1. Timeframe
Customers have 30 days from delivery to request a return.

## 2. Non-Returnable Items
The following goods cannot be returned:
- Gift cards
- Downloadable software products
- Custom-made or personalized items
""",
        encoding="utf-8",
    )

    service = PolicyRAGService(document_path=str(policy_file), top_k=2)
    context = service.build_context("I bought software yesterday and want to return it.")

    assert "Non-Returnable Items" in context
    assert "Downloadable software products" in context
    assert "Timeframe" not in context


def test_policy_rag_retrieves_across_multiple_policy_documents(tmp_path):
    refund_policy = tmp_path / "refund_policy.txt"
    refund_policy.write_text(
        """# Return and Refund Policy

## 1. Timeframe
Customers have 30 days from delivery to request a return.
""",
        encoding="utf-8",
    )
    delivery_policy = tmp_path / "delivery_policy.txt"
    delivery_policy.write_text(
        """DELIVERY POLICY

DELIVERY ISSUES
Delayed shipment
Lost package
Tracking number not updating

OWNER ASSIGNMENT
Logistics Team
""",
        encoding="utf-8",
    )
    account_policy = tmp_path / "account_policy.txt"
    account_policy.write_text(
        """ACCOUNT MANAGEMENT POLICY

ACCOUNT ISSUES COVERED
Login failures
Password reset requests
Account lockouts

OWNER ASSIGNMENT
Billing Team
""",
        encoding="utf-8",
    )
    escalation_policy = tmp_path / "escalation_policy.txt"
    escalation_policy.write_text(
        """ESCALATION POLICY

MANAGER ESCALATION CRITERIA
Threatens legal action
Requests executive review

OWNER ASSIGNMENT
Escalate to Manager
""",
        encoding="utf-8",
    )

    service = PolicyRAGService(
        document_paths=[
            str(refund_policy),
            str(delivery_policy),
            str(account_policy),
            str(escalation_policy),
        ],
        top_k=1,
    )

    delivery_context = service.build_context("My package is lost and tracking is not updating.")
    account_context = service.build_context("I cannot login because my account is locked.")
    escalation_context = service.build_context("I will take legal action and want executive review.")

    assert "Source: delivery_policy.txt" in delivery_context
    assert "Logistics Team" in delivery_context
    assert "Source: account_policy.txt" in account_context
    assert "Account lockouts" in account_context
    assert "Source: escalation_policy.txt" in escalation_context
    assert "Escalate to Manager" in escalation_context


def test_policy_rag_splits_long_sections_into_overlapping_chunks(tmp_path):
    policy_file = tmp_path / "delivery_policy.txt"
    policy_file.write_text(
        """DELIVERY POLICY

DELIVERY ISSUES
alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu
""",
        encoding="utf-8",
    )

    service = PolicyRAGService(
        document_paths=[str(policy_file)],
        chunk_token_size=5,
        chunk_token_overlap=2,
        embedding_dimensions=32,
        top_k=10,
    )
    chunks = service._load_chunks(policy_file, 5, 2, 32)

    assert len(chunks) > 1
    assert "alpha beta gamma delta epsilon" in chunks[0].text
    assert "delta epsilon zeta eta theta" in chunks[1].text


def test_policy_rag_chunks_include_local_embeddings(tmp_path):
    policy_file = tmp_path / "account_policy.txt"
    policy_file.write_text(
        """ACCOUNT MANAGEMENT POLICY

LOCKED ACCOUNT PROCEDURE
Customers with account lockouts require identity verification.
""",
        encoding="utf-8",
    )

    chunks = PolicyRAGService._load_chunks(policy_file, 120, 25, 32)

    assert chunks
    assert len(chunks[0].embedding) == 32
    assert any(value != 0 for value in chunks[0].embedding)


def test_triage_prompt_includes_retrieved_policy_context():
    prompt = build_user_message(
        "Can I return my order?",
        "Section: 1. Timeframe\nCustomers have 30 days from delivery.",
    )

    assert "Relevant policy context retrieved from the knowledge base" in prompt
    assert "Customers have 30 days from delivery" in prompt
