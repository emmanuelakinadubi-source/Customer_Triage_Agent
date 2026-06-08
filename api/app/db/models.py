from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class TriageRecord(Base):
    __tablename__ = "triage_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    message = Column(Text, nullable=False)
    category = Column(String(100))
    urgency = Column(String(20))
    urgency_reason = Column(Text)
    sentiment = Column(String(20))
    suggested_owner = Column(String(100))
    draft_response = Column(Text, nullable=True)
    confidence = Column(String(20))
    abusive_flag = Column(Boolean, default=False)
    guardrail_passed = Column(Boolean, default=True)
    guardrail_reason = Column(Text, nullable=True)
    mlflow_run_id = Column(String(100), nullable=True)
