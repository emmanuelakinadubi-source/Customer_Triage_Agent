import json
import csv
from io import StringIO

from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, Query
from sqlalchemy.orm import Session

from app.schemas.triage import (
    TriageRequest,
    TriageResponse,
    BatchTriageRequest,
    BatchItemResponse,
    TriageHistoryItem,
)
from app.services.triage_service import triage_service
from app.db.session import get_db
from app.db.models import TriageRecord

router = APIRouter(prefix="/triage", tags=["Customer Triage"])


@router.post("", response_model=TriageResponse)
async def create_triage(payload: TriageRequest, db: Session = Depends(get_db)):
    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="The message field cannot be empty.")
    return await triage_service.process_single_triage(payload.message, db)


@router.post("/batch", response_model=list[BatchItemResponse])
async def create_batch_triage(
    payload: BatchTriageRequest, db: Session = Depends(get_db)
):
    results = []
    for index, msg in enumerate(payload.messages):
        if not msg.strip():
            results.append(
                BatchItemResponse(
                    success=False,
                    review_id=index + 1,
                    input_message=msg,
                    error="Empty message",
                )
            )
            continue
        try:
            triage_output = await triage_service.process_single_triage(msg, db)
            results.append(
                BatchItemResponse(
                    success=True,
                    review_id=index + 1,
                    input_message=msg,
                    data=triage_output,
                )
            )
        except Exception as exc:
            results.append(
                BatchItemResponse(
                    success=False,
                    review_id=index + 1,
                    input_message=msg,
                    error=str(exc),
                )
            )
    return results


@router.get("/history", response_model=list[TriageHistoryItem])
def get_triage_history(
    limit: int = Query(default=50, le=200, description="Max records to return"),
    db: Session = Depends(get_db),
):
    records = (
        db.query(TriageRecord)
        .order_by(TriageRecord.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        TriageHistoryItem(
            id=r.id,
            created_at=r.created_at.isoformat() if r.created_at else None,
            message=r.message,
            category=r.category,
            urgency=r.urgency,
            urgency_reason=r.urgency_reason,
            sentiment=r.sentiment,
            suggested_owner=r.suggested_owner,
            draft_response=r.draft_response,
            confidence=r.confidence,
            abusive_flag=r.abusive_flag,
            guardrail_passed=r.guardrail_passed,
            mlflow_run_id=r.mlflow_run_id,
        )
        for r in records
    ]


@router.post("/upload", response_model=list[BatchItemResponse])
async def upload_batch_file(
    file: UploadFile = File(...), db: Session = Depends(get_db)
):
    contents = await file.read()

    try:
        decoded = contents.decode("utf-8")
    except UnicodeDecodeError:
        try:
            decoded = contents.decode("utf-8-sig")
        except UnicodeDecodeError:
            decoded = contents.decode("latin-1")

    messages_to_process = []

    if file.filename.endswith(".json"):
        try:
            parsed_data = json.loads(decoded)
            if isinstance(parsed_data, list):
                messages_to_process = [item.get("message", "") for item in parsed_data]
            elif isinstance(parsed_data, dict) and "messages" in parsed_data:
                messages_to_process = parsed_data["messages"]
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON structure.")

    elif file.filename.endswith(".csv"):
        f_io = StringIO(decoded)
        reader = csv.DictReader(f_io)
        for row in reader:
            if "message" in row:
                messages_to_process.append(row["message"])
            elif row.values():
                messages_to_process.append(list(row.values())[0])
    else:
        raise HTTPException(status_code=400, detail="Unsupported file type. Use CSV or JSON.")

    if not messages_to_process:
        raise HTTPException(status_code=400, detail="No messages found in file.")

    batch_payload = BatchTriageRequest(messages=messages_to_process[:20])
    return await create_batch_triage(batch_payload, db)
