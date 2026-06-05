from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="Customer Triage Agent API", version="0.1.0")


class TriagesRequest(BaseModel):
    message: str = Field(..., min_length=1)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/triage")
def triage(payload: TriagesRequest):
    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="message field cannot be empty")

    # Placeholder response for the scaffold
    return {
        "category": "General Enquiry",
        "urgency": "Low",
        "urgency_reason": "The message is a general request and does not indicate an immediate issue.",
        "sentiment": "Neutral",
        "suggested_owner": "Customer Service Agent",
        "draft_response": "Thank you for reaching out. We have received your message and will review it shortly.",
        "confidence": "Medium",
        "abusive_flag": False,
        "validation_status": "pending_implementation",
    }
