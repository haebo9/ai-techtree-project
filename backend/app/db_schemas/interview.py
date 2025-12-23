from datetime import datetime
from typing import List, Optional
from enum import Enum
from pydantic import BaseModel, Field
from .common import MongoDBModel, PyObjectId

class InterviewStatus(str, Enum):
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class InterviewMessage(BaseModel):
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class InterviewResult(BaseModel):
    is_passed: bool
    score: int  # 0~100
    feedback_message: str
    improvement_tip: Optional[str] = None
    evaluated_at: datetime = Field(default_factory=datetime.utcnow)

class InterviewMeta(BaseModel):
    skill_slug: str         # 대상 기술
    track_slug: Optional[str] = None # (Optional) 트랙 문맥
    target_level: int       # 도전 레벨 (1, 2, 3)
    status: InterviewStatus = InterviewStatus.IN_PROGRESS
    started_at: datetime = Field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = None

class Interview(MongoDBModel):
    """
    [Collection]: interviews
    사용자의 면접 세션 및 대화 로그
    """
    user_id: PyObjectId  # users._id 참조
    
    meta: InterviewMeta
    messages: List[InterviewMessage] = []
    result: Optional[InterviewResult] = None

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "60d5ecb8b5c9...",
                "meta": {
                    "skill_slug": "python",
                    "target_level": 2,
                    "status": "IN_PROGRESS"
                },
                "messages": [
                    {"role": "assistant", "content": "질문입니다."}
                ]
            }
        }
