"""
Integration tests for the /triage API routes.

triage_service.process_single_triage is patched with AsyncMock so tests
do not call Azure OpenAI or MLflow. The database is an in-memory SQLite
instance provided by the conftest fixtures.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch

from app.db.models import TriageRecord


PATCH_TARGET = "app.services.triage_service.triage_service.process_single_triage"


# ---------------------------------------------------------------------------
# POST /triage  — single message
# ---------------------------------------------------------------------------

class TestPostTriage:
    def test_valid_message_returns_200_with_triage_fields(self, client, sample_triage_response):
        with patch(PATCH_TARGET, new_callable=AsyncMock, return_value=sample_triage_response):
            response = client.post("/triage", json={"message": "I want a refund for my order."})

        assert response.status_code == 200
        data = response.json()
        assert data["category"] == "Refund Request"
        assert data["urgency"] == "Low"
        assert data["sentiment"] == "Negative"
        assert data["suggested_owner"] == "Billing Team"
        assert data["abusive_flag"] is False
        assert "draft_response" in data

    def test_whitespace_only_message_returns_422(self, client):
        # Pydantic strips whitespace in field_validator then min_length=1 rejects it.
        response = client.post("/triage", json={"message": "   "})
        assert response.status_code == 422

    def test_missing_message_field_returns_422(self, client):
        response = client.post("/triage", json={})
        assert response.status_code == 422

    def test_empty_string_returns_422_from_pydantic(self, client):
        response = client.post("/triage", json={"message": ""})
        assert response.status_code == 422

    def test_service_http_exception_is_propagated(self, client):
        from fastapi import HTTPException
        with patch(
            PATCH_TARGET,
            new_callable=AsyncMock,
            side_effect=HTTPException(status_code=422, detail="Guardrail validation failed: FAIL_ROUTING"),
        ):
            response = client.post("/triage", json={"message": "Test message."})
        assert response.status_code == 422
        assert "Guardrail" in response.json()["detail"]

    def test_abusive_message_flag_is_present_in_response(self, client, sample_triage_response):
        abusive = sample_triage_response.model_copy(
            update={"abusive_flag": True, "draft_response": None}
        )
        with patch(PATCH_TARGET, new_callable=AsyncMock, return_value=abusive):
            response = client.post("/triage", json={"message": "Offensive text here."})
        assert response.status_code == 200
        assert response.json()["abusive_flag"] is True


# ---------------------------------------------------------------------------
# GET /triage/history
# ---------------------------------------------------------------------------

class TestGetTriageHistory:
    def _seed_record(self, db_session, message="Test message", category="General Enquiry"):
        record = TriageRecord(
            message=message,
            category=category,
            urgency="Low",
            urgency_reason="A general customer query.",
            sentiment="Neutral",
            suggested_owner="Customer Service Agent",
            draft_response="We will look into this.",
            confidence="Medium",
            abusive_flag=False,
            created_at=datetime.utcnow(),
        )
        db_session.add(record)
        db_session.commit()
        return record

    def test_empty_history_returns_empty_list(self, client):
        response = client.get("/triage/history")
        assert response.status_code == 200
        assert response.json() == []

    def test_seeded_record_appears_in_history(self, client, db_session):
        self._seed_record(db_session, message="Where is my delivery?", category="Delivery Issue")

        response = client.get("/triage/history")
        assert response.status_code == 200
        records = response.json()
        assert len(records) == 1
        assert records[0]["message"] == "Where is my delivery?"
        assert records[0]["category"] == "Delivery Issue"

    def test_history_is_ordered_most_recent_first(self, client, db_session):
        from datetime import timedelta
        older = datetime.utcnow() - timedelta(seconds=10)
        newer = datetime.utcnow()

        for message, ts in [("First message", older), ("Second message", newer)]:
            db_session.add(TriageRecord(
                message=message,
                category="General Enquiry",
                urgency="Low",
                urgency_reason="Generic query.",
                sentiment="Neutral",
                suggested_owner="Customer Service Agent",
                confidence="Medium",
                abusive_flag=False,
                created_at=ts,
            ))
        db_session.commit()

        records = client.get("/triage/history").json()
        assert len(records) == 2
        assert records[0]["message"] == "Second message"

    def test_limit_parameter_restricts_returned_rows(self, client, db_session):
        for i in range(5):
            self._seed_record(db_session, message=f"Message {i}")

        response = client.get("/triage/history?limit=2")
        assert response.status_code == 200
        assert len(response.json()) == 2

    def test_history_response_includes_expected_fields(self, client, db_session):
        self._seed_record(db_session)

        record = client.get("/triage/history").json()[0]
        for field in ("id", "message", "category", "urgency", "sentiment",
                      "suggested_owner", "abusive_flag", "guardrail_passed", "created_at"):
            assert field in record


# ---------------------------------------------------------------------------
# POST /triage/upload  — file upload
# ---------------------------------------------------------------------------

class TestUploadBatchFile:
    def test_unsupported_file_type_returns_400(self, client):
        response = client.post(
            "/triage/upload",
            files={"file": ("notes.txt", b"hello world", "text/plain")},
        )
        assert response.status_code == 400
        assert "Unsupported" in response.json()["detail"]

    def test_csv_with_no_rows_returns_400(self, client):
        response = client.post(
            "/triage/upload",
            files={"file": ("data.csv", b"message\n", "text/csv")},
        )
        assert response.status_code == 400
        assert "No messages" in response.json()["detail"]

    def test_invalid_json_returns_400(self, client):
        response = client.post(
            "/triage/upload",
            files={"file": ("data.json", b"{{not valid json", "application/json")},
        )
        assert response.status_code == 400

    def test_valid_csv_upload_returns_200(self, client, sample_triage_response):
        csv_content = b"message\nI need a refund please\n"
        with patch(PATCH_TARGET, new_callable=AsyncMock, return_value=sample_triage_response):
            response = client.post(
                "/triage/upload",
                files={"file": ("data.csv", csv_content, "text/csv")},
            )
        assert response.status_code == 200
        results = response.json()
        assert len(results) == 1
        assert results[0]["success"] is True

    def test_valid_json_list_upload_returns_200(self, client, sample_triage_response):
        import json
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

    def test_json_upload_caps_at_20_messages(self, client, sample_triage_response):
        import json
        payload = json.dumps([{"message": f"msg {i}"} for i in range(25)]).encode()
        with patch(PATCH_TARGET, new_callable=AsyncMock, return_value=sample_triage_response):
            response = client.post(
                "/triage/upload",
                files={"file": ("data.json", payload, "application/json")},
            )
        assert response.status_code == 200
        assert len(response.json()) == 20
