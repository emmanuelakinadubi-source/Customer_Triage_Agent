from fastapi import HTTPException
from app.services.llm_service import llm_service
from app.guards.routing_guard import guardrail_check
from app.schemas.triage import TriageResponse

class TriageService:
    async def process_single_triage(self, message: str) -> TriageResponse:
        # 1. Primary classification extraction call
        raw_json = await llm_service.extract_triage(message)
        # 2. Extract values mapped for your guardrail input parameters
        category = raw_json.get("category")
        suggested_owner = raw_json.get("suggested_owner")
        urgency = raw_json.get("urgency")
        draft_response = raw_json.get("draft_response")
        urgency_reason = raw_json.get("urgency_reason")
        
        # 3. Process your custom guardrail logic
        guard_result = guardrail_check(
            category=category,
            owner=suggested_owner,
            urgency=urgency,
            draft_response=draft_response,
            original_message=message,
            client=llm_service.client,
            deployment=llm_service.deployment_name,
            urgency_reason=urgency_reason
        )
        if not guard_result["valid"]:
            raise HTTPException(
                status_code=422, 
                detail=f"Business Guardrail validation violation exception: {guard_result['reason']}"
            )
            
        return TriageResponse(
            category=category,
            urgency=urgency,
            urgency_reason=urgency_reason if urgency_reason else "",
            sentiment=raw_json.get("sentiment", "Neutral"),
            suggested_owner=suggested_owner,
            draft_response=draft_response,
            confidence=raw_json.get("confidence", "Medium"),
            abusive_flag=raw_json.get("abusive_flag", False)
        )

triage_service = TriageService()