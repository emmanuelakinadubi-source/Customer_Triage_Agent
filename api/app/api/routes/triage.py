import json
import csv
from io import StringIO
from fastapi import APIRouter, HTTPException, UploadFile, File
from app.schemas.triage import TriageRequest, TriageResponse, BatchTriageRequest, BatchItemResponse
from app.services.triage_service import triage_service

router = APIRouter(prefix="/triage", tags=["Customer Triage"])

@router.post("", response_model=TriageResponse)
async def create_triage(payload: TriageRequest):
    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="The message field cannot be empty.")
    return await triage_service.process_single_triage(payload.message)

@router.post("/batch", response_model=list[BatchItemResponse])
async def create_batch_triage(payload: BatchTriageRequest):
    results = []
    for index, msg in enumerate(payload.messages):
        if not msg.strip():
            results.append(BatchItemResponse(success=False, review_id=index+1, input_message=msg, error="Empty message context"))
            continue
        try:
            triage_output = await triage_service.process_single_triage(msg)
            results.append(BatchItemResponse(success=True, review_id=index+1, input_message=msg, data=triage_output))
        except Exception as e:
            results.append(BatchItemResponse(success=False, review_id=index+1, input_message=msg, error=str(e)))
    return results

@router.post("/upload", response_model=list[BatchItemResponse])
async def upload_batch_file(file: UploadFile = File(...)):
    contents = await file.read()
    
    # --- ROBUST DECODING FALLBACK LAYER ---
    try:
        decoded = contents.decode("utf-8")
    except UnicodeDecodeError:
        try:
            # Try utf-8-sig to catch Excel BOM exports
            decoded = contents.decode("utf-8-sig")
        except UnicodeDecodeError:
            # Fallback to latin-1 to safely decode Windows-1252 / cp1252 smart quotes & dashes
            decoded = contents.decode("latin-1")
    # --------------------------------------

    messages_to_process = []
    
    if file.filename.endswith(".json"):
        try:
            parsed_data = json.loads(decoded)
            if isinstance(parsed_data, list):
                messages_to_process = [item.get("message", "") for item in parsed_data]
            elif isinstance(parsed_data, dict) and "messages" in parsed_data:
                messages_to_process = parsed_data["messages"]
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid target structural JSON configuration data layout.")
            
    elif file.filename.endswith(".csv"):
        f_io = StringIO(decoded)
        reader = csv.DictReader(f_io)
        for row in reader:
            if "message" in row:
                messages_to_process.append(row["message"])
            elif row.values():
                # Fallback if header doesn't exactly match "message"
                messages_to_process.append(list(row.values())[0])
    else:
        raise HTTPException(status_code=400, detail="Unsupported upload file type format extension.")

    if not messages_to_process:
        raise HTTPException(status_code=400, detail="No trackable customer messages parsed.")
        
    payload = BatchTriageRequest(messages=messages_to_process[:20])
    return await create_batch_triage(payload)