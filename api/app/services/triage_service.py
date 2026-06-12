from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.services.langfuse_service import langfuse_service
from app.services.llm_service import llm_service
from app.guards.input_guard import check_input
from app.guards.output_guard import check_output, OutputGuardInput
from app.guards.return_policy_guard import apply_return_policy_guard
from app.schemas.triage import TriageResponse
from app.db.models import TriageRecord


class TriageService:
    async def process_single_triage(self, message: str, db: Session) -> TriageResponse:
        with langfuse_service.observation(
            name="customer-triage-request",
            as_type="span",
        ) as trace:
            trace.set_trace_io(input={"message": message})
            trace.update(tags=["customer-triage", "rag", "guardrails"])

            # 1. Input guard - fast deterministic check before any LLM call
            with langfuse_service.observation(name="input-guard", as_type="span") as input_span:
                input_result = check_input(message)
                input_span.update(
                    input={"message": message},
                    output=input_result.model_dump(),
                )
            if not input_result.valid:
                trace.set_trace_io(output={"error": input_result.reason})
                raise HTTPException(
                    status_code=400,
                    detail=f"Input validation failed: {input_result.reason}",
                )
            message = input_result.cleaned_message

            # 2. LLM extraction
            raw_json = await llm_service.extract_triage(message)
            with langfuse_service.observation(name="return-policy-guard", as_type="span") as policy_span:
                guarded_json = apply_return_policy_guard(message, raw_json)
                policy_span.update(
                    input={"message": message, "llm_output": raw_json},
                    output=guarded_json,
                    metadata={"overrode_llm_output": guarded_json != raw_json},
                )
            raw_json = guarded_json

            category        = raw_json.get("category")
            suggested_owner = raw_json.get("suggested_owner")
            urgency         = raw_json.get("urgency")
            draft_response  = raw_json.get("draft_response")
            urgency_reason  = raw_json.get("urgency_reason")

            # 3. Output guard - validates routing rules, hallucination, and LLM guardrail
            guard_input = OutputGuardInput(
                category=category,
                suggested_owner=suggested_owner,
                urgency=urgency,
                draft_response=draft_response,
                original_message=message,
                urgency_reason=urgency_reason,
                sentiment=raw_json.get("sentiment", "Neutral"),
                confidence=raw_json.get("confidence", "Medium"),
                abusive_flag=raw_json.get("abusive_flag", False),
            )
            with langfuse_service.observation(name="output-guard", as_type="span") as output_span:
                guard_result = check_output(
                    guard_input,
                    client=llm_service.client,
                    deployment=llm_service.deployment_name,
                )
                output_span.update(
                    input=guard_input.model_dump(),
                    output=guard_result.model_dump(),
                )

            if not guard_result.valid:
                trace.set_trace_io(output={"error": guard_result.reason})
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

            trace.set_trace_io(output=triage.model_dump())

            return triage


triage_service = TriageService()
