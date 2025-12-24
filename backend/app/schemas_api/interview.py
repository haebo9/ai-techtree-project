from pydantic import BaseModel
from typing import Optional

class InterviewCreate(BaseModel):
    user_id: str
    skill_slug: str
    target_level: int

class InterviewUpdate(BaseModel):
    status: Optional[str] = None
    result: Optional[dict] = None
