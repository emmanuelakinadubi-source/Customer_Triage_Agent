from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.services.llm_service import llm_service
from app.guards.input_guard import check_input
from app.guards.output_guard import check_output, OutputGuardInput
from app.schemas.triage import TriageResponse
from app.db.models import TriageRecord


class TriageService:
    async def process_single_triage(self, message: str, db: Session) -> TriageResponse:
        # 1. Input guard — fast deterministic check before any LLM call
        input_result = check_input(message)
        if not input_result.valid:
            raise HTTPException(
                status_code=400,
                detail=f"Input validation failed: {input_result.reason}",
            )
        message = input_result.cleaned_message

        # 2. LLM extraction
        raw_json = await llm_service.extract_triage(message)

        category        = raw_json.get("category")
        suggested_owner = raw_json.get("suggested_owner")
        urgency         = raw_json.get("urgency")
        draft_response  = raw_json.get("draft_response")
        urgency_reason  = raw_json.get("urgency_reason")

        # 3. Output guard — validates routing rules, hallucination, and LLM guardrail
        guard_result = check_output(
            OutputGuardInput(
                category=category,
                suggested_owner=suggested_owner,
                urgency=urgency,
                draft_response=draft_response,
                original_message=message,
                urgency_reason=urgency_reason,
            ),
            client=llm_service.client,
            deployment=llm_service.deployment_name,
        )

        if not guard_result.valid:
            raise HTTPException(
                status_code=422,
                detail=f"Guardrail validation failed: {guard_result.reason}",
            )

        triage = TriageResponse(
            category=category,
            urgency=urgency,
            urgency_reason=urgency_reason if urgency_reason else "",
            sentiment=raw_json.get("sentiment", "Neutral"),
            suggested_owner=suggested_owner,
            draft_response=draft_response,
            confidence=raw_json.get("confidence", "Medium"),
            abusive_flag=raw_json.get("abusive_flag", False),
        )

        # 4. Persist to database
        record = TriageRecord(
            message=message,
            category=triage.category,
            urgency=triage.urgency,
            urgency_reason=triage.urgency_reason,
            sentiment=triage.sentiment,
            suggested_owner=triage.suggested_owner,
            draft_response=triage.draft_response,
            confidence=triage.confidence,
            abusive_flag=triage.abusive_flag,
            guardrail_passed=guard_result.valid,
            guardrail_reason=guard_result.reason,
        )
        db.add(record)
        db.commit()

        return triage


triage_service = TriageService()
