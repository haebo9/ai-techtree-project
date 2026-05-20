from pydantic import BaseModel, EmailStr, Field
from typing import Any, List, Dict, Optional

class SendEmailRequest(BaseModel):
    email: EmailStr
    score: int
    strengths: List[str]
    weaknesses: List[str]
    qa_review: List[Dict[str, str]] = Field(default_factory=list)
    communication_feedback: Dict[str, Any] = Field(default_factory=dict)
    self_intro_feedback: Dict[str, Any] = Field(default_factory=dict)
    role_fit: Dict[str, Any] = Field(default_factory=dict)
    tool_traces: List[Dict[str, Any]] = Field(default_factory=list)
    transcripts: List[Dict[str, str]] = Field(default_factory=list)
    interview_date: Optional[str] = None
    interview_duration: Optional[str] = None
