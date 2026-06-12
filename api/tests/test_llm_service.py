from types import SimpleNamespace

import pytest
from langchain_core.messages import HumanMessage, SystemMessage

from app.schemas.triage import TriageResponse
from app.services.llm_service import LLMService
from app.services.ragas_service import RAGAS_CONTEXTS_KEY


class FakeTriageChain:
    def __init__(self, response: TriageResponse):
        self.response = response
        self.messages = None

    async def ainvoke(self, messages):
        self.messages = messages
        return self.response


@pytest.mark.asyncio
async def test_extract_triage_uses_langchain_structured_output(monkeypatch):
    expected = TriageResponse(
        category="Refund Request",
        urgency="Low",
        urgency_reason="Customer is asking about a refund.",
        sentiment="Neutral",
        suggested_owner="Billing Team",
        draft_response="Thanks for reaching out. We can help review your refund request.",
        confidence="High",
        abusive_flag=False,
    )
    fake_chain = FakeTriageChain(expected)
    service = LLMService()
    service.triage_chain = fake_chain

    monkeypatch.setattr(
        "app.services.llm_service.rag_service.retrieve",
        lambda _: [
            SimpleNamespace(
                source="refund_policy.txt",
                section="Refund Window",
                score=0.95,
                text="Items may be returned within 30 days.",
            )
        ],
    )

    result = await service.extract_triage("Can I get a refund?")

    assert {key: value for key, value in result.items() if key != RAGAS_CONTEXTS_KEY} == expected.model_dump()
    assert result[RAGAS_CONTEXTS_KEY] == [
        "Source: refund_policy.txt\nSection: Refund Window\nItems may be returned within 30 days."
    ]
    assert isinstance(fake_chain.messages[0], SystemMessage)
    assert isinstance(fake_chain.messages[1], HumanMessage)
    assert "Items may be returned within 30 days." in fake_chain.messages[1].content
