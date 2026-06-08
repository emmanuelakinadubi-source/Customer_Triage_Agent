import asyncio
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.services.llm_service import llm_service
from app.guards.routing_guard import guardrail_check
from app.schemas.triage import TriageResponse
from app.db.models import TriageRecord
from app.services.mlflow_service import log_triage_run


class TriageService:
    async def process_single_triage(self, message: str, db: Session) -> TriageResponse:
        # 1. LLM extraction
        raw_json = await llm_service.extract_triage(message)

        category       = raw_json.get("category")
        suggested_owner = raw_json.get("suggested_owner")
        urgency        = raw_json.get("urgency")
        draft_response = raw_json.get("draft_response")
        urgency_reason = raw_json.get("urgency_reason")

        # 2. Guardrail validation
        guard_result = guardrail_check(
            category=category,
            owner=suggested_owner,
            urgency=urgency,
            draft_response=draft_response,
            original_message=message,
            client=llm_service.client,
            deployment=llm_service.deployment_name,
            urgency_reason=urgency_reason,
        )

        guardrail_passed = guard_result.get("valid", True)
        guardrail_reason = guard_result.get("reason", "")

        if not guardrail_passed:
            raise HTTPException(
                status_code=422,
                detail=f"Guardrail validation failed: {guardrail_reason}",
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

        # 3. Log to MLflow in a thread (non-blocking)
        mlflow_run_id = await asyncio.to_thread(log_triage_run, raw_json, message)

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
            guardrail_passed=guardrail_passed,
            guardrail_reason=guardrail_reason,
            mlflow_run_id=mlflow_run_id,
        )
        db.add(record)
        db.commit()

        return triage


triage_service = TriageService()
