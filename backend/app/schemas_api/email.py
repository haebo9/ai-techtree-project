from pydantic import BaseModel, EmailStr
from typing import List, Dict, Any, Optional

class SendEmailRequest(BaseModel):
    email: EmailStr
    score: int
    strengths: List[str]
    weaknesses: List[str]
    qa_review: List[Dict[str, str]]
    job_recommendations: List[Dict[str, str]]
    transcripts: List[Dict[str, str]] = []
    interview_date: Optional[str] = None
    interview_duration: Optional[str] = None
