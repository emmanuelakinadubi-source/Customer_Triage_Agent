from fastapi import APIRouter, HTTPException
from typing import List

from ...schemas.triage import TriagesRequest, TriageResponse, BatchTriageRequest, BatchTriageResponse
from ...services.triage_service import triage_message

router = APIRouter()


@router.post("/triage", response_model=TriageResponse)
def triage(payload: TriagesRequest):
    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="message field cannot be empty")

    return triage_message(message)


@router.post("/triage/batch", response_model=BatchTriageResponse)
def triage_batch(payload: BatchTriageRequest):
    if not payload.messages:
        raise HTTPException(status_code=400, detail="messages array cannot be empty")

    results = []
    for message in payload.messages:
        message = str(message).strip()
        if not message:
            results.append({"message": message, "error": "Empty message"})
            continue

        try:
            result = triage_message(message)
            results.append({"message": message, **result})
        except Exception as ex:
            results.append({"message": message, "error": str(ex)})

    return {"results": results}
