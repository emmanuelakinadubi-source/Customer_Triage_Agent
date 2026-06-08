"""
Integration tests for POST /triage.

Covers:
  1. Empty message is rejected
  2. Missing message field is rejected
  3. Refund request classification
  4. Delivery issue classification
  5. Account problem routing
  6. Compliment classification
  7. Offensive language flagging
"""

import pytest
from unittest.mock import AsyncMock, patch

PATCH_TARGET = "app.services.triage_service.triage_service.process_single_triage"


def test_empty_message_is_rejected(client):
    """Item 1 — empty string is rejected before reaching the service."""
    response = client.post("/triage", json={"message": ""})
    assert response.status_code == 422


def test_missing_message_field_is_rejected(client):
    """Item 2 — request body without a message field is rejected."""
    response = client.post("/triage", json={})
    assert response.status_code == 422


def test_refund_request_classification(client, sample_triage_response):
    """Item 3 — refund message is classified as Refund Request."""
    with patch(PATCH_TARGET, new_callable=AsyncMock, return_value=sample_triage_response):
        response = client.post("/triage", json={"message": "I want a refund for my order."})

    assert response.status_code == 200
    data = response.json()
    assert data["category"] == "Refund Request"
    assert data["suggested_owner"] == "Billing Team"


def test_delivery_issue_classification(client, sample_triage_response):
    """Item 4 — delivery message is classified as Delivery Issue."""
    delivery_response = sample_triage_response.model_copy(update={
        "category": "Delivery Issue",
        "suggested_owner": "Logistics Team",
        "urgency_reason": "Customer reports a missing delivery.",
    })
    with patch(PATCH_TARGET, new_callable=AsyncMock, return_value=delivery_response):
        response = client.post("/triage", json={"message": "My package has not arrived."})

    assert response.status_code == 200
    data = response.json()
    assert data["category"] == "Delivery Issue"
    assert data["suggested_owner"] == "Logistics Team"


def test_account_problem_routing(client, sample_triage_response):
    """Item 5 — account message is routed to Billing Team or Customer Service Agent."""
    account_response = sample_triage_response.model_copy(update={
        "category": "Account Problem",
        "suggested_owner": "Billing Team",
        "urgency_reason": "Customer cannot access their account.",
    })
    with patch(PATCH_TARGET, new_callable=AsyncMock, return_value=account_response):
        response = client.post("/triage", json={"message": "I cannot log in to my account."})

    assert response.status_code == 200
    data = response.json()
    assert data["category"] == "Account Problem"
    assert data["suggested_owner"] in ("Billing Team", "Customer Service Agent")


def test_compliment_classification(client, sample_triage_response):
    """Item 6 — positive feedback message is classified as Compliment."""
    compliment_response = sample_triage_response.model_copy(update={
        "category": "Compliment",
        "suggested_owner": "Customer Service Agent",
        "sentiment": "Positive",
        "urgency": "Low",
        "urgency_reason": "Customer sent a positive message requiring no urgent action.",
    })
    with patch(PATCH_TARGET, new_callable=AsyncMock, return_value=compliment_response):
        response = client.post("/triage", json={"message": "Great service, thank you!"})

    assert response.status_code == 200
    data = response.json()
    assert data["category"] == "Compliment"
    assert data["sentiment"] == "Positive"


def test_offensive_language_flagging(client, sample_triage_response):
    """Item 7 — offensive message sets abusive_flag and suppresses draft_response."""
    abusive_response = sample_triage_response.model_copy(update={
        "abusive_flag": True,
        "draft_response": None,
    })
    with patch(PATCH_TARGET, new_callable=AsyncMock, return_value=abusive_response):
        response = client.post("/triage", json={"message": "This is offensive content."})

    assert response.status_code == 200
    data = response.json()
    assert data["abusive_flag"] is True
    assert data["draft_response"] is None
