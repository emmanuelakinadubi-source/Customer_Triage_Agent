"""
Tests for POST /triage/batch and POST /triage/upload batch processing.

Each test patches triage_service.process_single_triage so no real LLM
calls are made. The focus is on:
  - Correct handling of empty/whitespace messages within a batch
  - Sequential review_id assignment
  - Partial failure isolation (one bad message must not abort the rest)
  - File upload message extraction (CSV and JSON formats)
  - 20-message cap enforcement
"""

import json
import pytest
from unittest.mock import AsyncMock, patch

PATCH_TARGET = "app.services.triage_service.triage_service.process_single_triage"


# ---------------------------------------------------------------------------
# POST /triage/batch
# ---------------------------------------------------------------------------

class TestBatchEndpoint:
    def test_all_valid_messages_return_success(self, client, sample_triage_response):
        with patch(PATCH_TARGET, new_callable=AsyncMock, return_value=sample_triage_response):
            response = client.post(
                "/triage/batch",
                json={"messages": ["Refund request", "Where is my package?"]},
            )

        assert response.status_code == 200
        results = response.json()
        assert len(results) == 2
        assert all(r["success"] for r in results)

    def test_empty_message_in_batch_marked_as_failure(self, client, sample_triage_response):
        with patch(PATCH_TARGET, new_callable=AsyncMock, return_value=sample_triage_response):
            response = client.post(
                "/triage/batch",
                json={"messages": ["Valid message", "", "  "]},
            )

        assert response.status_code == 200
        results = response.json()
        successes = [r for r in results if r["success"]]
        failures = [r for r in results if not r["success"]]
        assert len(successes) == 1
        assert len(failures) == 2
        assert all(r["error"] == "Empty message" for r in failures)

    def test_review_ids_are_sequential_starting_at_one(self, client, sample_triage_response):
        with patch(PATCH_TARGET, new_callable=AsyncMock, return_value=sample_triage_response):
            response = client.post(
                "/triage/batch",
                json={"messages": ["msg a", "msg b", "msg c"]},
            )

        ids = [r["review_id"] for r in response.json()]
        assert ids == [1, 2, 3]

    def test_service_exception_on_one_message_does_not_abort_batch(self, client, sample_triage_response):
        call_count = 0

        async def side_effect(message, db):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise Exception("LLM unavailable")
            return sample_triage_response

        with patch(PATCH_TARGET, side_effect=side_effect):
            response = client.post(
                "/triage/batch",
                json={"messages": ["Message one", "Message two", "Message three"]},
            )

        assert response.status_code == 200
        results = response.json()
        assert results[0]["success"] is True
        assert results[1]["success"] is False
        assert "LLM unavailable" in results[1]["error"]
        assert results[2]["success"] is True

    def test_batch_response_includes_input_message_field(self, client, sample_triage_response):
        with patch(PATCH_TARGET, new_callable=AsyncMock, return_value=sample_triage_response):
            response = client.post(
                "/triage/batch",
                json={"messages": ["I need a refund"]},
            )

        result = response.json()[0]
        assert result["input_message"] == "I need a refund"

    def test_twenty_one_messages_rejected_by_schema_validation(self, client):
        response = client.post(
            "/triage/batch",
            json={"messages": [f"message {i}" for i in range(21)]},
        )
        assert response.status_code == 422

    def test_empty_messages_list_rejected(self, client):
        response = client.post("/triage/batch", json={"messages": []})
        assert response.status_code == 422

    def test_successful_result_contains_triage_data(self, client, sample_triage_response):
        with patch(PATCH_TARGET, new_callable=AsyncMock, return_value=sample_triage_response):
            response = client.post(
                "/triage/batch",
                json={"messages": ["Please process my refund"]},
            )

        result = response.json()[0]
        assert result["success"] is True
        assert result["data"]["category"] == "Refund Request"
        assert result["data"]["urgency"] == "Low"


# ---------------------------------------------------------------------------
# POST /triage/upload — message extraction from CSV and JSON
# ---------------------------------------------------------------------------

class TestUploadMessageExtraction:
    def test_csv_message_column_extracted_correctly(self, client, sample_triage_response):
        csv_content = b"message\nI want a refund\nWhere is my order\n"
        with patch(PATCH_TARGET, new_callable=AsyncMock, return_value=sample_triage_response):
            response = client.post(
                "/triage/upload",
                files={"file": ("data.csv", csv_content, "text/csv")},
            )
        assert response.status_code == 200
        assert len(response.json()) == 2

    def test_csv_without_message_column_falls_back_to_first_column(self, client, sample_triage_response):
        csv_content = b"text\nI want a refund\n"
        with patch(PATCH_TARGET, new_callable=AsyncMock, return_value=sample_triage_response):
            response = client.post(
                "/triage/upload",
                files={"file": ("data.csv", csv_content, "text/csv")},
            )
        assert response.status_code == 200
        assert len(response.json()) == 1

    def test_json_list_of_objects_extracted_correctly(self, client, sample_triage_response):
        payload = json.dumps([
            {"message": "Refund for order"},
            {"message": "Package not received"},
        ]).encode()
        with patch(PATCH_TARGET, new_callable=AsyncMock, return_value=sample_triage_response):
            response = client.post(
                "/triage/upload",
                files={"file": ("data.json", payload, "application/json")},
            )
        assert response.status_code == 200
        assert len(response.json()) == 2

    def test_json_dict_with_messages_key_extracted_correctly(self, client, sample_triage_response):
        payload = json.dumps({"messages": ["First message", "Second message"]}).encode()
        with patch(PATCH_TARGET, new_callable=AsyncMock, return_value=sample_triage_response):
            response = client.post(
                "/triage/upload",
                files={"file": ("data.json", payload, "application/json")},
            )
        assert response.status_code == 200
        assert len(response.json()) == 2

    def test_upload_caps_batch_at_20_messages(self, client, sample_triage_response):
        rows = "\n".join(f"Message number {i}" for i in range(25))
        csv_content = f"message\n{rows}\n".encode()
        with patch(PATCH_TARGET, new_callable=AsyncMock, return_value=sample_triage_response):
            response = client.post(
                "/triage/upload",
                files={"file": ("data.csv", csv_content, "text/csv")},
            )
        assert response.status_code == 200
        assert len(response.json()) == 20

    def test_csv_with_latin1_encoding_is_accepted(self, client, sample_triage_response):
        # Byte 0x97 is an em-dash in Windows-1252/latin-1.
        csv_content = "message\nI want a refund \x97 urgent\n".encode("latin-1")
        with patch(PATCH_TARGET, new_callable=AsyncMock, return_value=sample_triage_response):
            response = client.post(
                "/triage/upload",
                files={"file": ("data.csv", csv_content, "text/csv")},
            )
        # The API upload endpoint handles decoding; the request should succeed.
        assert response.status_code == 200
