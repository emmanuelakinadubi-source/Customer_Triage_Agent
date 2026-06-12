from contextlib import contextmanager
from unittest.mock import AsyncMock, patch

import pytest

from app.guards.routing_guard import GuardrailResult
from app.services.ragas_service import RAGAS_CONTEXTS_KEY
from app.services.triage_service import triage_service


class RecordingObservation:
    def update(self, **kwargs):
        return None

    def set_trace_io(self, **kwargs):
        return None

    def score(self, **kwargs):
        return None


recording_observation = RecordingObservation()


@contextmanager
def noop_observation(*args, **kwargs):
    yield recording_observation


@pytest.mark.asyncio
async def test_triage_logs_ragas_scores_to_langfuse(db_session):
    llm_output = {
        "category": "Refund Request",
        "urgency": "Low",
        "urgency_reason": "Customer wants refund policy help.",
        "sentiment": "Neutral",
        "suggested_owner": "Billing Team",
        "draft_response": "Software products are non-returnable under the refund policy.",
        "confidence": "High",
        "abusive_flag": False,
        RAGAS_CONTEXTS_KEY: [
            "Source: refund_policy.txt\nSection: Non-Returnable Items\nDownloadable software products cannot be returned."
        ],
    }

    with (
        patch(
            "app.services.triage_service.llm_service.extract_triage",
            new_callable=AsyncMock,
            return_value=llm_output,
        ),
        patch(
            "app.services.triage_service.check_output",
            return_value=GuardrailResult(valid=True, reason="All checks passed"),
        ),
        patch(
            "app.services.triage_service.ragas_service.evaluate_response",
            new_callable=AsyncMock,
            return_value={
                "faithfulness": 1.0,
                "answer_relevancy": 0.92,
                "context_precision": 0.88,
                "context_recall": 0.95,
            },
        ) as evaluate_response,
        patch("app.services.triage_service.langfuse_service.enabled", True),
        patch("app.services.triage_service.langfuse_service.observation", noop_observation),
        patch("app.services.triage_service.langfuse_service.score_current_trace") as score_current_trace,
    ):
        triage = await triage_service.process_single_triage(
            "I bought software yesterday and want to return it for a refund.",
            db_session,
        )

    assert triage.category == "Refund Request"
    evaluate_response.assert_awaited_once()
    assert score_current_trace.call_count == 4
    score_names = {call.kwargs["name"] for call in score_current_trace.call_args_list}
    assert score_names == {
        "ragas_faithfulness",
        "ragas_answer_relevancy",
        "ragas_context_precision",
        "ragas_context_recall",
    }
