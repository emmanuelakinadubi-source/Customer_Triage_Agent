"""
Integration test for POST /triage/batch.

Covers:
  8. Batch endpoint processing
"""

import pytest
from unittest.mock import AsyncMock, patch

PATCH_TARGET = "app.services.triage_service.triage_service.process_single_triage"


def test_batch_endpoint_processes_multiple_messages(client, sample_triage_response):
    """Item 8 — batch endpoint returns a result for each submitted message."""
    with patch(PATCH_TARGET, new_callable=AsyncMock, return_value=sample_triage_response):
        response = client.post(
            "/triage/batch",
            json={"messages": [
                "I want a refund for my order.",
                "My package has not arrived.",
                "I cannot log in to my account.",
            ]},
        )

    assert response.status_code == 200
    results = response.json()
    assert len(results) == 3
    assert all(r["success"] for r in results)
    assert all("category" in r["data"] for r in results)
