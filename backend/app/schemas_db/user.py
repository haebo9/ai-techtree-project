from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, EmailStr
from .common import MongoDBModel

# --- Sub Models (Embedded Documents) ---

class AuthInfo(BaseModel):
    email: EmailStr
    provider: str  # e.g., 'kakao', 'google'
    uid: str       # Provider's unique user ID

class UserProfile(BaseModel):
    nickname: str
    avatar_url: Optional[str] = None
    job_title: Optional[str] = None

class UserStats(BaseModel):
    total_stars: int = 0
    completed_tracks: List[str] = []



class KeywordProgress(BaseModel):
    """
    사용자의 키워드(Keyword)별 숙련도 (v1.1)
    """
    level: int = 0  # 0~5 (0: New, 1: Novice, 2: Intermediate, 3: Advanced, 4: Expert, 5: Master)
    score: float = 0.0 # Continuous score based on evaluation
    last_reviewed_at: Optional[datetime] = None
    successful_attempts: int = 0

# --- Main Collection Model ---

class User(MongoDBModel):
    """
    [Collection]: users
    사용자 정보 및 학습 상태(Skill Tree)를 저장
    """
    auth: AuthInfo
    profile: UserProfile
    stats: UserStats = Field(default_factory=UserStats)
    
    # [User State] 학습 진행도
    # Key: Subject Title (e.g., 'FastAPI Essentials') -> 빠른 조회를 위해 Map 구조 사용
    # Legacy: skill_tree: Dict[str, SubjectProgress] = Field(default_factory=dict)

    # [User State v1.1] 키워드별 학습 숙련도
    # Key: Keyword Key (e.g. "Dependency Injection")
    keyword_progress: Dict[str, KeywordProgress] = Field(default_factory=dict)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "auth": {
                    "email": "user@example.com",
                    "provider": "kakao",
                    "uid": "12345"
                },
                "profile": {
                    "nickname": "AI_Master"
                },
                "skill_tree": {
                    "FastAPI Essentials": {"level": 2, "stars": 2}
                }
            }
        }
