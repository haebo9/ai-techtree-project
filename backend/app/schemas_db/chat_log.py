from datetime import datetime
from pydantic import BaseModel, Field
from .common import MongoDBModel

class LogSummary(BaseModel):
    score: int = 0
    total_count: int = 0
    max_level: int = 0
    is_completed: bool = False

class ChatLog(MongoDBModel):
    """
    [Collection]: chat_logs
    키워드별 전체 대화 이력을 통째로 저장 (분석용)
    """
    keyword: str         # 검색/그룹핑의 핵심 ID
    user_id: str         # 대화 주체
    session_id: str      # thread_id (중복 저장 방지용)
    
    # 분석용 통계 필드 (v1.3 추가)
    summary: LogSummary = Field(default_factory=LogSummary)

    # 전체 대화 이력을 하나의 텍스트로 합친 값
    full_conversation: str 
    
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "keyword": "Python",
                "user_id": "user@example.com",
                "session_id": "thread_123",
                "full_conversation": "[User]: Python 공부할래.\n[AI]: 좋습니다! ...",
                "created_at": "2024-03-02T14:30:00Z"
            }
        }
