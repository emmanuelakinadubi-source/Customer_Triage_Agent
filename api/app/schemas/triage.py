from typing import List, Optional
from pydantic import BaseModel, Field


class TriageResponse(BaseModel):
    category: str
    urgency: str
    urgency_reason: str
    sentiment: str
    suggested_owner: str
    draft_response: Optional[str] = None
    confidence: str
    abusive_flag: bool


class TriageResultItem(BaseModel):
    message: str
    category: Optional[str] = None
    urgency: Optional[str] = None
    urgency_reason: Optional[str] = None
    sentiment: Optional[str] = None
    suggested_owner: Optional[str] = None
    draft_response: Optional[str] = None
    confidence: Optional[str] = None
    abusive_flag: Optional[bool] = None
    validation_status: Optional[str] = None
    error: Optional[str] = None


class BatchTriageResponse(BaseModel):
    results: List[TriageResultItem]


class TriageRequest(BaseModel):
    message: str = Field(..., min_length=1, description="Raw customer text message")

class BatchTriageRequest(BaseModel):
    messages: List[str] = Field(..., min_length=1, max_length=20)


class BatchItemResponse(BaseModel):
    success: bool
    review_id: int
    input_message: str
    data: Optional[TriageResponse] = None
    error: Optional[str] = None