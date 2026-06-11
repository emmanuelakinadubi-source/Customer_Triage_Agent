from unittest.mock import AsyncMock, patch

import pytest

from app.guards.routing_guard import GuardrailResult
from app.guards.return_policy_guard import (
    NON_RETURNABLE_ITEM_RESPONSE,
    OUTSIDE_RETURN_WINDOW_RESPONSE,
)
from app.services.triage_service import triage_service


@pytest.mark.asyncio
async def test_return_policy_guard_overrides_llm_draft_for_exact_user_message(db_session):
    wrong_llm_output = {
        "category": "Refund Request",
        "urgency": "Low",
        "urgency_reason": "Customer wants to return a previously delivered item.",
        "sentiment": "Mixed",
        "suggested_owner": "Customer Service Agent",
        "draft_response": (
            "Thank you for contacting us. We understand you would like to return "
            "your item and we are here to assist you with the return process."
        ),
        "confidence": "High",
        "abusive_flag": False,
    }

    with (
        patch(
            "app.services.triage_service.llm_service.extract_triage",
            new_callable=AsyncMock,
            return_value=wrong_llm_output,
        ),
        patch(
            "app.services.triage_service.check_output",
            return_value=GuardrailResult(valid=True, reason="All checks passed"),
        ),
    ):
        triage = await triage_service.process_single_triage(
            "i recieved my package 3 months ago it was really good but now i kinda dont like it and want to return it",
            db_session,
        )

    assert triage.draft_response == OUTSIDE_RETURN_WINDOW_RESPONSE
    assert "within 30 days" in triage.draft_response
    assert "outside the return policy timeframe" in triage.draft_response
    assert "support team" not in triage.draft_response


@pytest.mark.asyncio
async def test_return_policy_guard_overrides_llm_draft_for_gift_card_return(db_session):
    wrong_llm_output = {
        "category": "Refund Request",
        "urgency": "Low",
        "urgency_reason": "Customer wants to return a gift card.",
        "sentiment": "Neutral",
        "suggested_owner": "Customer Service Agent",
        "draft_response": (
            "Thank you for contacting us. To assist you with your return request "
            "for the Amazon gift card, could you please provide the delivery date "
            "so we can check your eligibility for a return?"
        ),
        "confidence": "High",
        "abusive_flag": False,
    }

    with (
        patch(
            "app.services.triage_service.llm_service.extract_triage",
            new_callable=AsyncMock,
            return_value=wrong_llm_output,
        ),
        patch(
            "app.services.triage_service.check_output",
            return_value=GuardrailResult(valid=True, reason="All checks passed"),
        ),
    ):
        triage = await triage_service.process_single_triage(
            "i ordered a amazon gift card which i recieved yesterday but i want to return it",
            db_session,
        )

    assert triage.draft_response == NON_RETURNABLE_ITEM_RESPONSE
    assert "non-returnable" in triage.draft_response
    assert "support team" not in triage.draft_response
