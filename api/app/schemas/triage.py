from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

# ---------------------------------------------------------------------------
# Constrained types — shared across request/response models
# ---------------------------------------------------------------------------

CategoryType = Literal[
    "Refund Request",
    "Delivery Issue",
    "Product Complaint",
    "Account Problem",
    "General Enquiry",
    "Compliment",
    "Other",
]

UrgencyType = Literal["High", "Medium", "Low"]

SentimentType = Literal["Positive", "Negative", "Neutral", "Mixed"]

OwnerType = Literal[
    "Customer Service Agent",
    "Billing Team",
    "Logistics Team",
    "Escalate to Manager",
]

ConfidenceType = Literal["High", "Medium", "Low"]


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class TriageRequest(BaseModel):
    message: str = Field(..., min_length=1, description="Raw customer text message")

    @field_validator("message", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        if isinstance(v, str):
            return v.strip()
        return v


class BatchTriageRequest(BaseModel):
    messages: List[str] = Field(..., min_length=1, max_length=20)


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class TriageResponse(BaseModel):
    category: CategoryType
    urgency: UrgencyType
    urgency_reason: str
    sentiment: SentimentType
    suggested_owner: OwnerType
    draft_response: Optional[str] = None
    confidence: ConfidenceType
    abusive_flag: bool


class TriageResultItem(BaseModel):
    message: str
    category: Optional[CategoryType] = None
    urgency: Optional[UrgencyType] = None
    urgency_reason: Optional[str] = None
    sentiment: Optional[SentimentType] = None
    suggested_owner: Optional[OwnerType] = None
    draft_response: Optional[str] = None
    confidence: Optional[ConfidenceType] = None
    abusive_flag: Optional[bool] = None
    validation_status: Optional[str] = None
    error: Optional[str] = None


class BatchTriageResponse(BaseModel):
    results: List[TriageResultItem]


class BatchItemResponse(BaseModel):
    success: bool
    review_id: int
    input_message: str
    data: Optional[TriageResponse] = None
    error: Optional[str] = None


class TriageHistoryItem(BaseModel):
    id: int
    created_at: Optional[str] = None
    message: str
    category: Optional[str] = None
    urgency: Optional[str] = None
    urgency_reason: Optional[str] = None
    sentiment: Optional[str] = None
    suggested_owner: Optional[str] = None
    draft_response: Optional[str] = None
    confidence: Optional[str] = None
    abusive_flag: Optional[bool] = None
    guardrail_passed: Optional[bool] = None
