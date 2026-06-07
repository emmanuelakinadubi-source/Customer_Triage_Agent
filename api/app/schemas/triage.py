from typing import List, Optional
from pydantic import BaseModel, Field


class TriagesRequest(BaseModel):
    message: str = Field(..., min_length=1)


class TriageResponse(BaseModel):
    category: str
    urgency: str
    urgency_reason: str
    sentiment: str
    suggested_owner: str
    draft_response: str
    confidence: str
    abusive_flag: bool
    validation_status: str


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


class BatchTriageRequest(BaseModel):
    messages: List[str] = Field(..., min_items=1)


class BatchTriageResponse(BaseModel):
    results: List[TriageResultItem]
